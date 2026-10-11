"""central/jra/program: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.normalize.central_feed import normalize_central_race
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time


from arvexq.ingest.central.jra.state import JRA_MEETING_DAY_RE
from arvexq.ingest.central.jra.state import JRA_TRACK_CODE_BY_NAME
from arvexq.ingest.central.jra.state import _jra_program_cache
from arvexq.ingest.central.jra.state import _jra_program_cache_lock
from arvexq.ingest.central.jra.state import JRA_CNAME_RE
from arvexq.ingest.central.jra.state import _jra_cname_lookup
from arvexq.ingest.central.jra.state import _jra_cname_lookup_lock

def _jra_program_summaries(iso_date: str, *, _jra_program_title, _jra_request, _jra_text, _today_iso) -> list[dict]:
    now=time.time()
    with _jra_program_cache_lock:
        hit=_jra_program_cache.get(iso_date)
        if hit and now-hit[0]<(60 if iso_date==_today_iso() else 86400):return [dict(x) for x in hit[1]]
    try:d=datetime.strptime(iso_date,"%Y-%m-%d")
    except Exception:return []
    url=f"https://www.jra.go.jp/keiba/calendar{d.year}/{d.year}/{d.month}/{d.strftime('%m%d')}.html"
    try:html=_jra_request(url,None,60 if iso_date==_today_iso() else 86400)
    except Exception:return []
    soup=BeautifulSoup(html,"html.parser"); out=[]
    for table in soup.find_all("table"):
        head=_jra_text(table.find("thead") or table.find("tr") or table)
        if "レース番号" not in head or "発走時刻" not in head:continue
        track="";meeting_no=0;day_no=0
        prev=table.find_previous(string=JRA_MEETING_DAY_RE)
        if prev:
            mt=JRA_MEETING_DAY_RE.search(str(prev))
            if mt:meeting_no=int(mt.group(1));track=mt.group(2);day_no=int(mt.group(3))
        if not track:
            node=table.find_previous(["h2","h3","h4","h5","strong","p","div"]);guard=0
            while node is not None and guard<30:
                mt=JRA_MEETING_DAY_RE.search(_jra_text(node))
                if mt:meeting_no=int(mt.group(1));track=mt.group(2);day_no=int(mt.group(3));break
                node=node.find_previous(["h2","h3","h4","h5","strong","p","div"]);guard+=1
        if not track:continue
        track_code=JRA_TRACK_CODE_BY_NAME.get(track,"")
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"])
            if len(cells)<3:continue
            c0,c1,c2=(_jra_text(cells[0]),_jra_text(cells[1]),_jra_text(cells[2]))
            rm=re.search(r"(\d{1,2})\s*レース",c0)
            if not rm:continue
            race_no=int(rm.group(1))
            dm=re.search(r"([\d,]{4,5})\s*[（(]([^）)]+)[）)]",c1)
            distance=int(dm.group(1).replace(",","")) if dm else 0;desc=dm.group(2) if dm else ""
            surface="障害" if "障害" in c1 else ("芝" if "芝" in desc else ("ダート" if "ダ" in desc else ""))
            sm=re.search(r"(\d{1,2})時\s*(\d{2})分",c2)
            start=f"{int(sm.group(1)):02d}:{sm.group(2)}" if sm else ""
            title=_jra_program_title(c1) or f"{race_no}R"
            nkid=(f"{d.year:04d}{track_code}{meeting_no:02d}{day_no:02d}{race_no:02d}" if track_code and meeting_no and day_no else "")
            z=normalize_central_race({"id":f"jra-{iso_date}-{track}-{race_no:02d}","date":iso_date,"track":track,"raceNumber":race_no,"title":title,"distance":distance,"surface":surface,"condition":"不明","weather":"不明","fieldSize":0,"racePrize1":0,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"JRA競馬番組","_summaryOnly":True,"meetingNumber":meeting_no,"meetingDay":day_no,"netkeibaRaceId":nkid})
            if z:out.append(z)
    out.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    with _jra_program_cache_lock:_jra_program_cache[iso_date]=(now,[dict(x) for x in out])
    return out


def _jra_program_lookup(iso_date: str, track: str, race_no: int, *, _jra_program_summaries):
    for r in _jra_program_summaries(iso_date):
        if str(r.get("track"))==str(track) and int(r.get("raceNumber") or 0)==int(race_no):return dict(r)
    return None


def _jra_find_cname(iso_date: str, track: str, race_no: int, *, _jra_norm_cname, _jra_race_no_from_cname, _jra_request, _jra_track_from_cname) -> str:
    key=(iso_date,track,int(race_no))
    with _jra_cname_lookup_lock:
        if key in _jra_cname_lookup:return _jra_cname_lookup[key]
    token=iso_date.replace("-","")
    try:home=_jra_request("https://www.jra.go.jp/",None,60)
    except Exception:return ""
    seeds=[]
    for c in JRA_CNAME_RE.findall(home):
        c=_jra_norm_cname(c)
        if token in c and c not in seeds:seeds.append(c)
    candidates=list(seeds)
    def live_first(items):
        # JRA exposes a basic card (pw01dde01...) and the live/full card
        # (pw01dde10...). The live/full variant carries current odds + body weight.
        return sorted(items,key=lambda c:(0 if "pw01dde10" in c else 1,0 if token in c else 1,c))
    for seed in seeds[:8]:
        try:page=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",seed,30)
        except Exception:continue
        for c in JRA_CNAME_RE.findall(page):
            c=_jra_norm_cname(c)
            if token in c and c not in candidates:candidates.append(c)
        for c in live_first(candidates):
            if _jra_track_from_cname(c)==track and _jra_race_no_from_cname(c)==int(race_no):
                with _jra_cname_lookup_lock:_jra_cname_lookup[key]=c
                return c
    for c in live_first(candidates):
        if _jra_track_from_cname(c)==track and _jra_race_no_from_cname(c)==int(race_no):
            with _jra_cname_lookup_lock:_jra_cname_lookup[key]=c
            return c
    return ""
