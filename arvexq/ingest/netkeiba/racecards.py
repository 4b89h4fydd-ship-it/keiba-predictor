"""netkeiba/racecards: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.supplemental import _parse_recent_cell
from arvexq.normalize.scalars import _clean
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import os
import re
import time


def _netkeiba_detail_rows(detail: dict, *, _netkeiba_get, _netkeiba_race_id, _nk_row_horse) -> list[dict]:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return []
    url=f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}";past=f"https://race.netkeiba.com/race/shutuba_past.html?race_id={rid}&rf=shutuba_submenu"
    html="";past_html=""
    timeout=float(os.getenv("NETKEIBA_DETAIL_TIMEOUT_SEC","3.5"))
    def _get_now():
        try:return _netkeiba_get(url,timeout,20)
        except Exception as exc:print("netkeiba detail failed",rid,exc);return ""
    def _get_past():
        try:return _netkeiba_get(past,timeout,180)
        except Exception as exc:print("netkeiba past failed",rid,exc);return ""
    with ThreadPoolExecutor(max_workers=2) as pool:
        f1=pool.submit(_get_now);f2=pool.submit(_get_past);html=f1.result() or "";past_html=f2.result() or ""
    rows={}
    if html:
        soup=BeautifulSoup(html,"html.parser")
        for tr in soup.select("tr.HorseList"):
            horse=_nk_row_horse(tr)
            if not horse:continue
            rows[horse["horseNumber"]]=horse
    if past_html:
        soup=BeautifulSoup(past_html,"html.parser")
        for tr in soup.select("tr.HorseList"):
            horse=_nk_row_horse(tr)
            if not horse:continue
            key=horse["horseNumber"]
            if key not in rows:rows[key]=horse
            rr=[]
            for td in tr.find_all("td"):
                z=_parse_recent_cell(td.get_text(" ",strip=True))
                if z:rr.append(z)
                if len(rr)>=5:break
            if rr:rows[key]["recentRaces"]=rr[:5]
    return list(rows.values())


def _nar_netkeiba_preview_rows(detail: dict, force: bool=False, *, _nar_netkeiba_race_id, _netkeiba_get) -> dict:
    """Fallback before NAR live odds/weights appear: use netkeiba's current NAR card.
    Predicted odds are explicitly tagged and are replaced by official live odds later.
    """
    rid=_nar_netkeiba_race_id(str(detail.get('date') or ''),str(detail.get('track') or ''),int(detail.get('raceNumber') or 0))
    if not rid:return {}
    url=f"https://nar.netkeiba.com/race/shutuba.html?race_id={rid}"
    if force:url+=f"&t={int(time.time()*1000)}"
    try:html=_netkeiba_get(url,float(os.getenv('NETKEIBA_NAR_TIMEOUT_SEC','3.5')),0 if force else 30)
    except Exception as exc:
        print('NAR netkeiba preview failed',rid,exc);return {}
    soup=BeautifulSoup(html,'html.parser');full=_clean(soup.get_text(' ',strip=True));forecast_page='予想オッズ' in full
    out={};field_count=0
    for tr in soup.select('tr.HorseList'):
        field_count+=1
        txt=_clean(tr.get_text(' ',strip=True));no=0
        um=tr.find('td',class_=re.compile(r'Umaban',re.I))
        if um:
            mm=re.search(r'\d{1,2}',_clean(um.get_text(' ',strip=True)));no=int(mm.group()) if mm else 0
        if not no:
            mm=re.match(r'\D*(\d{1,2})\D+',txt);no=int(mm.group(1)) if mm else 0
        if not no:continue
        odd=None;pop=None
        odds_span=tr.find('span',id=re.compile(r'^odds-1_'))
        ns=tr.find('span',id=re.compile(r'^ninki-1_'))
        if odds_span:
            mo=re.search(r'\d+(?:\.\d+)?',_clean(odds_span.get_text(' ',strip=True)));odd=float(mo.group()) if mo else None
        if ns:
            mp=re.search(r'\d+',_clean(ns.get_text(' ',strip=True)));pop=int(mp.group()) if mp else None
        if odd is None:
            mo=re.search(r'(?<!\d)(\d{1,3}(?:\.\d+)?)\s*[（(]\s*(\d{1,2})人気\s*[）)]',txt)
            if mo:odd=float(mo.group(1));pop=int(mo.group(2))
        bw=None;chg=None
        wt=tr.select_one('td.Weight')
        wtxt=_clean(wt.get_text(' ',strip=True)) if wt else txt
        bm=re.search(r'(?<!\d)(\d{3})\s*kg?\s*[（(]\s*([+\-]?\d+)\s*[）)]',wtxt)
        if not bm:bm=re.search(r'(?<!\d)(\d{3})\s*[（(]\s*([+\-]?\d+)\s*[）)]',wtxt)
        if bm:bw=int(bm.group(1));chg=int(bm.group(2))
        if odd is None and bw is None:continue
        z={}
        if odd and odd>1:
            z.update({'winOdds':odd,'popularity':pop,'oddsSource':'netkeiba予想オッズ' if forecast_page else 'netkeiba実オッズ','oddsForecast':bool(forecast_page)})
        if bw:
            z['bodyWeight']=bw;z['bodyWeightChange']=chg
        out[no]=z
    # v247: shutuba can omit the odds cells even while netkeiba's dedicated
    # NAR odds page already has them. Pull that page directly and merge the live
    # single-win odds so the full-day expected-value scan is not stuck at 0/N.
    field_count=max(field_count if 'field_count' in locals() else 0,len(out))
    have_odds=sum(1 for z in out.values() if (z or {}).get('winOdds'))
    if force or have_odds<max(3,int(max(1,field_count)*.65)):
        odds_url=f"https://nar.netkeiba.com/odds/index.html?race_id={rid}&type=b1"
        if force:odds_url+=f"&t={int(time.time()*1000)}"
        try:
            oh=_netkeiba_get(odds_url,float(os.getenv('NETKEIBA_NAR_ODDS_TIMEOUT_SEC','3.2')),0 if force else 12)
            osoup=BeautifulSoup(oh,'html.parser')
            for table in osoup.find_all('table'):
                headers=[_clean(x.get_text(' ',strip=True)).replace(' ','') for x in table.find_all('th')]
                if not headers:continue
                def hi(*parts):
                    for j,hv in enumerate(headers):
                        if any(p in hv for p in parts):return j
                    return -1
                ino=hi('馬番');iodd=hi('単勝オッズ','オッズ');ipop=hi('人気')
                if ino<0 or iodd<0:continue
                # Some tables include grouped/multi-row headers; use rows with enough td cells only.
                for tr in table.find_all('tr'):
                    cells=tr.find_all('td')
                    if not cells:continue
                    vals=[_clean(td.get_text(' ',strip=True)) for td in cells]
                    if max(ino,iodd)>=len(vals):continue
                    try:no=int(re.sub(r'\D','',vals[ino]) or 0)
                    except Exception:no=0
                    if no<=0 or no>30:continue
                    mo=re.search(r'\d+(?:\.\d+)?',vals[iodd].replace(',',''))
                    if not mo:continue
                    try:odd=float(mo.group())
                    except Exception:continue
                    if odd<=1:continue
                    pop=None
                    if 0<=ipop<len(vals):
                        mp=re.search(r'\d+',vals[ipop])
                        if mp:
                            try:pop=int(mp.group())
                            except Exception:pop=None
                    z=out.setdefault(no,{})
                    z['winOdds']=odd;z['oddsSource']='netkeiba実オッズ';z['oddsForecast']=False
                    if pop:z['popularity']=pop
        except Exception as exc:
            print('NAR netkeiba odds-page fallback failed',rid,exc)
    return out


def _netkeiba_card_rows_fast(detail: dict, *, _netkeiba_get, _netkeiba_race_id, _nk_row_horse) -> list[dict]:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return []
    try:
        html=_netkeiba_get(
            f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}",
            float(os.getenv("FAST_CARD_TIMEOUT_SEC","1.2")),20
        )
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser");rows=[]
    for tr in soup.select("tr.HorseList"):
        horse=_nk_row_horse(tr)
        if not horse:continue
        horse["source"]="netkeiba高速出走表"
        rows.append(horse)
    return rows


def _netkeiba_race_meta(detail: dict, *, _netkeiba_get, _netkeiba_race_id) -> dict:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return {}
    try:html=_netkeiba_get(f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}",float(os.getenv("NETKEIBA_DETAIL_TIMEOUT_SEC","3.5")),20)
    except Exception:return {}
    soup=BeautifulSoup(html,"html.parser");full=_clean(soup.get_text(" ",strip=True));out={}
    h1=soup.find("h1")
    if h1:out["title"]=_clean(h1.get_text(" ",strip=True))
    sm=re.search(r"(\d{1,2}:\d{2})発走",full)
    if sm:out["startTime"]=sm.group(1)
    dm=re.search(r"(?:芝|ダ|障)(\d{3,4})m",full)
    if dm:out["distance"]=int(dm.group(1))
    wm=re.search(r"天候[:：]?\s*(晴|曇|雨|小雨|雪|小雪)",full)
    if wm:out["weather"]=wm.group(1)
    cm=re.search(r"馬場[:：]?\s*(良|稍重|重|不良)",full)
    if cm:out["condition"]=cm.group(1)
    return out
