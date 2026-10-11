"""local/odds: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.pure_parsers import _jra_decode
from arvexq.normalize.scalars import _clean
from arvexq.normalize.scalars import _scratch_status
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re
import time
import urllib.parse
import urllib.request


from arvexq.ingest.local.state import NAR_BABA_CODES
from arvexq.ingest.local.state import _nar_odds_cache
from arvexq.ingest.local.state import _nar_odds_cache_lock

def _parse_nar_live_odds_html(html: str) -> dict:
    """Parse NAR official 単・複 page across header and positional layouts."""
    if not html:return {}
    soup=BeautifulSoup(html,"html.parser")
    out={}

    # Header-driven layout.
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if not rows:continue
        header=[];header_idx=-1
        for ri,tr in enumerate(rows[:4]):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if any("馬番" in x for x in vals) and any("単勝" in x for x in vals):
                header=vals;header_idx=ri;break
        if not header:continue

        def idxpart(part):
            for i,x in enumerate(header):
                if part in x:return i
            return -1

        ino=idxpart("馬番");iodd=idxpart("単勝");ipop=idxpart("人気");ibw=idxpart("馬体重")
        for tr in rows[header_idx+1:]:
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if ino<0 or ino>=len(vals) or iodd<0 or iodd>=len(vals):continue
            mn=re.fullmatch(r"\D*(\d{1,2})\D*",vals[ino])
            if not mn:continue
            no=int(mn.group(1))
            om=re.search(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)",vals[iodd])
            odds=float(om.group(1)) if om else 0.0
            scratch_status=_scratch_status(vals[iodd])
            pop=0
            if ipop>=0 and ipop<len(vals):
                pm=re.search(r"\d+",vals[ipop]);pop=int(pm.group()) if pm else 0
            bw=0;chg=None
            if ibw>=0 and ibw<len(vals):
                bm=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",vals[ibw])
                if bm:
                    bw=int(bm.group(1));chg=int(bm.group(2)) if bm.group(2) is not None else None
            if odds<=0 and not bw and not scratch_status:
                continue
            out[no]={"winOdds":odds or None,"popularity":pop or None,"bodyWeight":bw or None,
                     "bodyWeightChange":chg,"oddsSource":"NAR公式" if odds else "NAR公式出馬表",
                     "status":scratch_status,"scratched":bool(scratch_status)}

    # Current official layout second pass:
    # 枠 | 馬番 | 馬名 | 単勝 | 複勝下限 | 複勝上限 | 性齢 | 馬体重 ...
    # Always run this pass, even when the header-driven pass already found odds.
    # NAR uses multi-row/rowspan headers and the header index can be shifted for
    # 馬体重 on only one runner. Previously `if not out` skipped this reliable
    # flat-row pass as soon as odds existed, leaving cases such as the last horse
    # with odds but bodyWeight=None. Merge the flat row into missing live fields.
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"])]
            if len(vals)<4:continue
            m0=re.fullmatch(r"\d{1,2}",vals[0])
            m1=re.fullmatch(r"\d{1,2}",vals[1]) if len(vals)>1 else None
            oddm=re.fullmatch(r"\d+(?:\.\d+)?",vals[3]) if len(vals)>3 else None
            scratch_status=_scratch_status(vals[3] if len(vals)>3 else "")
            if not (m0 and m1 and (oddm or scratch_status)):continue
            no=int(m1.group());odds=float(oddm.group()) if oddm else 0.0
            if no<=0 or (odds<=0 and not scratch_status):continue
            bw=0;chg=None
            for cell in vals[6:10]:
                bm=re.search(r"(\d{3})\s*(?:[（(]\s*([+\-]?\d+)\s*[）)])?",cell)
                if bm:
                    bw=int(bm.group(1));chg=int(bm.group(2)) if bm.group(2) is not None else None
                    break
            z=out.setdefault(no,{})
            if odds>0:z["winOdds"]=odds
            if bw:
                z["bodyWeight"]=bw
                z["bodyWeightChange"]=chg
            z["oddsSource"]="NAR公式" if odds else z.get("oddsSource","")
            if scratch_status:
                z["status"]=scratch_status;z["scratched"]=True
            else:
                z.setdefault("status","");z.setdefault("scratched",False)

    ranked=sorted((float(v["winOdds"]),no) for no,v in out.items() if v.get("winOdds"))
    rank=0;last=None
    for ix,(odd,no) in enumerate(ranked,1):
        if last is None or odd!=last:rank=ix
        if not out[no].get("popularity"):out[no]["popularity"]=rank
        last=odd
    return out


def _nar_live_odds(track: str, iso_date: str, race_no: int, force: bool=False, *, _parse_nar_live_odds_html) -> dict:
    code=NAR_BABA_CODES.get(str(track or "").strip())
    if not code:return {}
    key=f"{code}|{iso_date}|{race_no}";now=time.time();ttl=int(os.getenv("NAR_LIVE_ODDS_CACHE_SEC","20"))
    with _nar_odds_cache_lock:
        hit=_nar_odds_cache.get(key)
        if hit and not force and now-hit[0]<ttl:return hit[1]

    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":iso_date.replace("-","/"),"k_raceNo":int(race_no),"t":int(time.time()*1000) if force else ""})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/OddsTanFuku_ipat?"+q,
    ]
    out={}
    for url in urls:
        req=urllib.request.Request(url,headers={
            "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
            "Accept-Language":"ja-JP,ja;q=0.9",
            "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
        })
        try:
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_ODDS_TIMEOUT_SEC","2.5"))) as res:
                html=_jra_decode(res.read())
            out=_parse_nar_live_odds_html(html)
            if out:break
        except Exception as exc:
            print("NAR odds fetch failed",track,iso_date,race_no,url,exc)

    with _nar_odds_cache_lock:
        _nar_odds_cache[key]=(now,out)
        if len(_nar_odds_cache)>64:
            oldest=min(_nar_odds_cache.items(),key=lambda kv:kv[1][0])[0];_nar_odds_cache.pop(oldest,None)
    return out


def _attach_nar_live_odds(detail: dict, *, _nar_live_odds) -> dict:
    if not detail:return detail
    odds=_nar_live_odds(str(detail.get("track") or ""),str(detail.get("date") or ""),int(detail.get("raceNumber") or 0))
    if not odds:return detail
    for h in detail.get("horses",[]) or []:
        z=odds.get(int(h.get("horseNumber") or 0))
        if z:h.update({k:v for k,v in z.items() if v is not None and v!=""})
    detail["oddsSource"]="NAR公式"; detail["oddsType"]="単勝実オッズ"; detail["oddsUpdatedAt"]=datetime.now().strftime("%H:%M:%S")
    return detail
