"""netkeiba/program: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.normalize.central_feed import normalize_central_race
from arvexq.normalize.scalars import _clean
from bs4 import BeautifulSoup
import os
import re


from arvexq.ingest.netkeiba.state import NETKEIBA_TRACK_CODES
from arvexq.ingest.central.jra.state import JRA_TRACK_CODE_BY_NAME
from arvexq.ingest.local.state import NAR_NETKEIBA_CODES

def _netkeiba_race_summaries(iso_date: str, *, _netkeiba_get, _today_iso) -> list[dict]:
    token=iso_date.replace("-","");url=f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={token}"
    try:html=_netkeiba_get(url,float(os.getenv("NETKEIBA_LIST_TIMEOUT_SEC","3.5")),30 if iso_date==_today_iso() else 86400)
    except Exception as exc:
        print("netkeiba list failed",iso_date,exc);return []
    soup=BeautifulSoup(html,"html.parser");out={}
    for a in soup.find_all("a",href=re.compile(r"race_id=(\d{12})")):
        href=str(a.get("href") or "");m=re.search(r"race_id=(\d{12})",href)
        if not m:continue
        rid=m.group(1);code=rid[4:6];track=NETKEIBA_TRACK_CODES.get(code)
        if not track:continue
        race_no=int(rid[-2:]);node=a
        for _ in range(4):
            if node.parent is None:break
            node=node.parent
            tx=_clean(node.get_text(" ",strip=True))
            if re.search(rf"(?:^|\s){race_no}R(?:\s|$)",tx):break
        tx=_clean(node.get_text(" ",strip=True) if node else a.get_text(" ",strip=True))
        mm=re.search(rf"(?:^|\s){race_no}R\s*(.*?)\s+(\d{{1,2}}:\d{{2}})\s+((?:芝|ダ|障)[^\s]*?)(\d{{3,4}})m(?:\s+(\d+)頭)?",tx)
        title="";start="";surf="";dist=0;field=0
        if mm:
            title=_clean(mm.group(1));start=mm.group(2);kind=mm.group(3);dist=int(mm.group(4));field=int(mm.group(5) or 0);surf="障害" if kind.startswith("障") else ("芝" if kind.startswith("芝") else "ダート")
        else:
            t=re.sub(rf"^.*?{race_no}R\s*","",tx);tm=re.search(r"\b\d{1,2}:\d{2}\b",t)
            if tm:title=_clean(t[:tm.start()]);start=tm.group(0)
            dm=re.search(r"(?:芝|ダ|障)[^0-9]*(\d{3,4})m",t)
            if dm:dist=int(dm.group(1));surf="芝" if "芝" in dm.group(0) else ("障害" if "障" in dm.group(0) else "ダート")
            fm=re.search(r"(\d+)頭",t);field=int(fm.group(1)) if fm else 0
        if not title:title=f"{race_no}R"
        z=normalize_central_race({"id":f"jra-{iso_date}-{track}-{race_no:02d}","date":iso_date,"track":track,"raceNumber":race_no,"title":title,"distance":dist,"surface":surf,"condition":"不明","weather":"不明","fieldSize":field,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"netkeiba一覧","netkeibaRaceId":rid,"_summaryOnly":True})
        if z:out[(track,race_no)]=z
    rows=list(out.values());rows.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    return rows


def _netkeiba_program_race_id(iso_date: str, track: str, race_no: int, *, _jra_program_lookup) -> str:
    try:
        p=_jra_program_lookup(iso_date,track,race_no) or {}
        rid=str(p.get("netkeibaRaceId") or "")
        if re.fullmatch(r"\d{12}",rid):return rid
        code=JRA_TRACK_CODE_BY_NAME.get(str(track or ""),"")
        meet=int(p.get("meetingNumber") or 0);day=int(p.get("meetingDay") or 0)
        year=int(str(iso_date)[:4]) if re.match(r"^20\d{2}",str(iso_date)) else 0
        if year and code and meet and day and int(race_no)>0:return f"{year:04d}{code}{meet:02d}{day:02d}{int(race_no):02d}"
    except Exception:pass
    return ""


def _netkeiba_race_id(iso_date: str, track: str, race_no: int, *, _netkeiba_program_race_id, _netkeiba_race_summaries) -> str:
    rid=_netkeiba_program_race_id(iso_date,track,race_no)
    if rid:return rid
    for r in _netkeiba_race_summaries(iso_date):
        if str(r.get("track"))==str(track) and int(r.get("raceNumber") or 0)==int(race_no):return str(r.get("netkeibaRaceId") or "")
    return ""


def _nar_netkeiba_race_id(iso_date: str, track: str, race_no: int) -> str:
    code=NAR_NETKEIBA_CODES.get(str(track or '').strip())
    m=re.match(r'^(20\d{2})-(\d{2})-(\d{2})$',str(iso_date or ''))
    if not code or not m or int(race_no)<=0:return ''
    return f"{m.group(1)}{code}{m.group(2)}{m.group(3)}{int(race_no):02d}"
