"""netkeiba/results: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.market import _parse_payouts
from arvexq.normalize.scalars import _clean
from bs4 import BeautifulSoup
import os
import re


def _netkeiba_current_result(detail: dict, *, _jra_parse_time_seconds, _netkeiba_get, _netkeiba_race_id) -> dict | None:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0))
    if not rid:return None
    try:html=_netkeiba_get(f"https://race.netkeiba.com/race/result.html?race_id={rid}",float(os.getenv("NETKEIBA_RESULT_TIMEOUT_SEC","3.0")),20)
    except Exception as exc:
        print("netkeiba result failed",rid,exc);return None
    soup=BeautifulSoup(html,"html.parser"); table=None; headers=[]
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr")[:4]:
            vals=[re.sub(r"\s+","",_clean(c.get_text(" ",strip=True))) for c in tr.find_all(["th","td"])]
            if any("着順" in v for v in vals) and any("馬番" in v for v in vals) and any("馬名" in v for v in vals):
                table=tb;headers=vals;break
        if table:break
    if table is None:return None
    def hidx(*keys):
        for i,v in enumerate(headers):
            for k in keys:
                if k in v:return i
        return -1
    i_fin=hidx("着順");i_frame=hidx("枠");i_no=hidx("馬番");i_name=hidx("馬名");i_time=hidx("タイム");i_corner=hidx("コーナー通過順");i_pop=hidx("人気");i_odds=hidx("単勝オッズ","単勝");i_bw=hidx("馬体重")
    finishers=[]
    for tr in table.find_all("tr"):
        tds=tr.find_all("td")
        if not tds:continue
        vals=[_clean(td.get_text(" ",strip=True)) for td in tds]
        def val(i):return vals[i] if 0<=i<len(vals) else ""
        fm=re.search(r"\d+",val(i_fin)) if i_fin>=0 else None
        fin=int(fm.group()) if fm else 0; no=0; frame=0
        mn=re.search(r"\d+",val(i_no)) if i_no>=0 else None
        mf=re.search(r"\d+",val(i_frame)) if i_frame>=0 else None
        if mn:no=int(mn.group())
        if mf:frame=int(mf.group())
        if not no:
            um=tr.find("td",class_=re.compile(r"Umaban",re.I))
            mm=re.search(r"\d+",_clean(um.get_text(" ",strip=True))) if um else None
            if mm:no=int(mm.group())
        name=val(i_name)
        if not name:
            na=tr.select_one(".Horse_Name a,.HorseInfo a,.Horse_Name")
            name=_clean(na.get_text(" ",strip=True)) if na else ""
        tm=_jra_parse_time_seconds(val(i_time)) if i_time>=0 else 0.0
        corners=[]
        cs=val(i_corner)
        cm=re.search(r"\d{1,2}(?:-\d{1,2})+",cs)
        if cm:corners=[int(x) for x in cm.group().split("-")]
        pop=None;odd=None;bw=None;chg=None
        mp=re.search(r"\d+",val(i_pop)) if i_pop>=0 else None
        if mp:
            try:pop=int(mp.group())
            except Exception:pass
        mo=re.search(r"\d+(?:\.\d+)?",val(i_odds)) if i_odds>=0 else None
        if mo:
            try:odd=float(mo.group())
            except Exception:pass
        mb=re.search(r"(\d{3})(?:\s*[（(]\s*([+\-]?\d+)\s*[）)])?",val(i_bw)) if i_bw>=0 else None
        if mb:
            try:bw=int(mb.group(1));chg=int(mb.group(2)) if mb.group(2) is not None else None
            except Exception:pass
        if no and name:finishers.append({"finish":fin,"finishLabel":str(fin)+"着" if fin else val(i_fin),"horseNumber":no,"frameNumber":frame,"name":name,"timeSeconds":tm,"cornerPositions":corners,"winOdds":odd,"popularity":pop,"bodyWeight":bw,"bodyWeightChange":chg})
    finishers.sort(key=lambda x:(int(x.get("finish") or 999),int(x.get("horseNumber") or 999)))
    if len(finishers)<3:return None
    payouts=_parse_payouts(soup)
    status="確定" if payouts or re.search(r"確定",_clean(soup.get_text(" ",strip=True))) else "速報"
    return {"status":status,"finishers":finishers,"source":"netkeiba結果","payouts":payouts}
