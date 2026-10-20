"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_program_summaries(iso_date:str)->list[dict]:
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
        meeting_no,track,day_no=jra_meeting_schedule(table,JRA_MEETING_DAY_RE,_jra_text)
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
            race_grade,race_class=jra_grade_class(c1)
            nkid=(f"{d.year:04d}{track_code}{meeting_no:02d}{day_no:02d}{race_no:02d}" if track_code and meeting_no and day_no else "")
            z=normalize_central_race({"id":f"jra-{iso_date}-{track}-{race_no:02d}","date":iso_date,"track":track,"raceNumber":race_no,"title":title,"raceGrade":race_grade,"raceClass":race_class,"distance":distance,"surface":surface,"condition":"不明","weather":"不明","fieldSize":0,"racePrize1":0,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"JRA競馬番組","_summaryOnly":True,"meetingNumber":meeting_no,"meetingDay":day_no,"netkeibaRaceId":nkid})
            if z:out.append(z)
    out.sort(key=lambda x:(str(x.get("track") or ""),int(x.get("raceNumber") or 0)))
    with _jra_program_cache_lock:_jra_program_cache[iso_date]=(now,[dict(x) for x in out])
    return out

def _jra_program_lookup(iso_date:str,track:str,race_no:int):
    for r in _jra_program_summaries(iso_date):
        if str(r.get("track"))==str(track) and int(r.get("raceNumber") or 0)==int(race_no):return dict(r)
    return None
