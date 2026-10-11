"""local/results: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.market import _parse_payouts
from arvexq.ingest.pure_parsers import _jra_decode
from arvexq.normalize.scalars import _clean
from bs4 import BeautifulSoup
import os
import re
import urllib.parse
import urllib.request


from arvexq.ingest.local.state import NAR_BABA_CODES

def _fetch_nar_payouts_only(detail: dict) -> tuple[list[dict], str]:
    code=NAR_BABA_CODES.get(detail.get("track"))
    if not code:return [],"競馬場コード未取得"
    query=urllib.parse.urlencode({
        "k_babaCode":code,
        "k_raceDate":str(detail.get("date") or "").replace("-","/"),
        "k_raceNo":int(detail.get("raceNumber") or 0),
    })
    urls=[
        "https://www.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_RefundMoneyList?"+query,
        "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_RefundMoneyList?"+query,
    ]
    last=""
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja,en-US;q=0.8",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_PAYOUT_TIMEOUT_SEC","2.0"))) as response:
                html=_jra_decode(response.read())
            payouts=_parse_payouts(BeautifulSoup(html,"html.parser"))
            if payouts:return payouts,url
            last="払戻表は取得したが解析結果0件"
        except Exception as exc:
            last=str(exc)
    return [],last or "払い戻し未取得"


def _attach_nar_payouts(detail: dict, *, _fetch_nar_payouts_only) -> dict:
    result=detail.get("result")
    if not isinstance(result,dict):
        result={}
        detail["result"]=result
    if result.get("payouts"):return detail
    payouts,source=_fetch_nar_payouts_only(detail)
    if payouts:
        result["payouts"]=payouts
        result["status"]="確定"
        result["payoutSource"]="NAR公式"
        result["payoutUrl"]=source
        result.pop("payoutError",None)
    else:
        result["payoutError"]="払い戻し未取得"
        result["payoutDebug"]=source[:240]
    return detail


def _nar_result_should_be_available(detail: dict, grace_min: int=1, *, _now_jst, _today_iso) -> bool:
    date=str(detail.get("date") or "")
    if not date:return False
    if date<_today_iso():return True
    if date>_today_iso():return False
    st=str(detail.get("startTime") or detail.get("scheduledStartTime") or "")
    m=re.match(r"^(\d{1,2}):(\d{2})",st)
    if not m:return False
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    return nowm>=int(m.group(1))*60+int(m.group(2))+int(grace_min)


def _nar_official_result_fast(detail: dict, *, _env_clean_condition, _env_clean_weather) -> dict | None:
    """Fetch NAR official RaceMarkTable directly; includes result, body weight and corner order."""
    code=NAR_BABA_CODES.get(str(detail.get("track") or "").strip())
    date=str(detail.get("date") or "")
    race_no=int(detail.get("raceNumber") or 0)
    if not code or not date or not race_no:return None
    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":date.replace("-","/"),"k_raceNo":race_no})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/RaceMarkTable_ipat?"+q,
    ]
    known={_clean(h.get("name")):int(h.get("horseNumber") or 0) for h in detail.get("horses",[]) or [] if h.get("name")}
    last_err=""
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja-JP,ja;q=0.9",
                "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_RESULT_TIMEOUT_SEC","4.0"))) as res:
                html=_jra_decode(res.read())
        except Exception as exc:
            last_err=str(exc);continue
        if not html:continue
        soup=BeautifulSoup(html,"html.parser")
        full=_clean(soup.get_text(" ",strip=True))
        if "競走成績" not in full and "着順" not in full:continue
        wm=re.search(r"天候\s*[：:]?\s*(小雨|小雪|晴|曇|雨|雪)",full)
        cm=re.search(r"馬場(?:状態)?\s*[：:]?\s*(不良|稍重|重|良)",full)
        finishers=[]
        for table in soup.find_all("table"):
            rows=table.find_all("tr")
            if not rows:continue
            headers=[];header_i=-1
            for ri,tr in enumerate(rows[:4]):
                vals=[_clean(c.get_text(" ",strip=True)) for c in tr.find_all(["th","td"],recursive=False)]
                joined="|".join(vals)
                if "着順" in joined and "馬体重" in joined and "馬番" in joined:
                    headers=vals;header_i=ri;break
            if not headers:continue
            def hi(part):
                for i,x in enumerate(headers):
                    if part in x:return i
                return -1
            idx={k:hi(v) for k,v in {
                "fin":"着順","frame":"枠","no":"馬番","name":"馬名","sexage":"性齢",
                "cw":"負担","jockey":"騎手","trainer":"調教師","bw":"馬体重",
                "time":"タイム","corner":"コーナー","pop":"人気","odds":"単勝"
            }.items()}
            for tr in rows[header_i+1:]:
                cells=tr.find_all(["th","td"],recursive=False)
                vals=[_clean(c.get_text(" ",strip=True)) for c in cells]
                if not vals:continue
                def val(key):
                    j=idx.get(key,-1)
                    return vals[j] if j>=0 and j<len(vals) else ""
                fin_txt=val("fin") or vals[0]
                mf=re.match(r"^\s*(\d+)\s*$",fin_txt)
                if not mf:continue
                fin=int(mf.group(1))
                name=val("name")
                no=0
                mno=re.search(r"\d+",val("no")) if val("no") else None
                if mno:no=int(mno.group())
                if not no and name:no=known.get(_clean(name),0)
                if not no:
                    for nm,hno in known.items():
                        if nm and nm in _clean(tr.get_text(" ",strip=True)):
                            no=hno;name=name or nm;break
                if not no:continue
                fr=0;mfr=re.search(r"\d+",val("frame")) if val("frame") else None
                if mfr:fr=int(mfr.group())
                bw=None;chg=None
                bwtxt=val("bw") or _clean(tr.get_text(" ",strip=True))
                mbw=re.search(r"(?<!\d)(\d{3,4})\s*(?:kg)?\s*[（(]\s*([+\-]?\d+)\s*[）)]",bwtxt)
                if mbw:bw=int(mbw.group(1));chg=int(mbw.group(2))
                tm=0.0;mt=re.search(r"(\d+):(\d{2}(?:\.\d+)?)",val("time"))
                if mt:tm=int(mt.group(1))*60+float(mt.group(2))
                corners=[]
                ctext=val("corner")
                mcorn=re.search(r"(?<!\d)(\d{1,2}(?:-\d{1,2}){1,4})(?!\d)",ctext)
                if mcorn:
                    try:corners=[int(x) for x in mcorn.group(1).split("-")]
                    except Exception:corners=[]
                pop=None;mp=re.search(r"\d+",val("pop")) if val("pop") else None
                if mp:pop=int(mp.group())
                odd=None;mo=re.search(r"\d+(?:\.\d+)?",val("odds")) if val("odds") else None
                if mo:
                    try:odd=float(mo.group())
                    except Exception:odd=None
                finishers.append({
                    "finish":fin,"finishLabel":f"{fin}着","horseNumber":no,
                    "frameNumber":fr or int((no+1)//2),"name":name or next((nm for nm,hno in known.items() if hno==no),""),
                    "timeSeconds":tm,"last3FSeconds":last3f,"cornerPositions":corners,"bodyWeight":bw,"bodyWeightChange":chg,
                    "popularity":pop,"winOdds":odd,
                })
            if finishers:break
        finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
        # Do not call a partial page final until at least the podium is visible.
        classified=[int(x.get("finish") or 0) for x in finishers if int(x.get("finish") or 0)>0]
        if 1 not in classified or sum(1 for finish in classified if finish<=3)<3:continue
        payouts=_parse_payouts(soup)
        explicit_final=bool(re.search(r"確定",full)) and not bool(re.search(r"速報|暫定",full))
        out={"status":"確定" if explicit_final else "速報","finishers":finishers,"source":"NAR公式競走成績","payouts":payouts}
        if wm:out["weather"]=_env_clean_weather(wm.group(1))
        if cm:out["condition"]=_env_clean_condition(cm.group(1))
        out["sourceUrl"]=url
        return out
    if last_err:print("NAR official result unavailable",detail.get("id"),last_err)
    return None
