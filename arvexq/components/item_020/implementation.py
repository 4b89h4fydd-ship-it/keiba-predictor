"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _jra_request(url: str, cname: str | None = None, cache_sec: int = 1800) -> str:
    key=url+"|"+(cname or "")
    now=time.time()
    with _jra_cache_lock:
        hit=_jra_text_cache.get(key)
        if hit and now-hit[0] < cache_sec:
            return hit[1]
    headers={"User-Agent":"Mozilla/5.0 (compatible; KeibaPredictor/6.2; +https://www.jra.go.jp/)","Accept-Language":"ja,en;q=0.8"}
    data=None
    if cname:
        data=urllib.parse.urlencode({"cname":cname}).encode("ascii")
        headers["Content-Type"]="application/x-www-form-urlencoded"
    req=urllib.request.Request(url,data=data,headers=headers)
    with urllib.request.urlopen(req,timeout=float(os.getenv("JRA_OFFICIAL_TIMEOUT_SEC","4.5"))) as res:
        text=_jra_decode(res.read())
    with _jra_cache_lock:
        _jra_text_cache[key]=(now,text)
    return text

def _jra_norm_cname(value:str)->str:
    return re.sub(r"%2F","/",str(value or ""),flags=re.I)

def _jra_attr_cname(tag, pattern) -> str:
    if not tag: return ""
    blob=" ".join(str(v) for v in tag.attrs.values())+" "+str(tag)
    m=pattern.search(blob)
    return _jra_norm_cname(m.group(0)) if m else ""

def _jra_program_title(info:str)->str:
    s=re.sub(r"\s+"," ",str(info or "")).strip(); dm=re.search(r"[\d,]{4,5}\s*[（(]",s); prefix=(s[:dm.start()] if dm else s).strip()
    cm=re.search(r"\s+(?:障害)?(?:2歳|3歳|4歳)(?:以上)?",prefix)
    if cm and cm.start()>0:
        named=prefix[:cm.start()].strip()
        if named:return named
    return prefix

def _jra_find_cname(iso_date:str,track:str,race_no:int)->str:
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

def _jra_text(tag) -> str:
    return re.sub(r"\s+"," ",tag.get_text(" ",strip=True) if tag else "").strip()

def _jra_parse_race(cname:str, supplement_profiles: bool = True)->dict|None:
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    cache_sec=int(os.getenv("JRA_LIVE_ODDS_CACHE_SEC","45")) if date==_today_iso() else 600
    try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,cache_sec)
    except Exception:return None
    # The basic dde01 card can omit live fields even while the official dde10
    # card for the same race already contains them. Prefer the official live card.
    if date==_today_iso() and "pw01dde10" not in cname:
        live=[]
        for cc in JRA_CNAME_RE.findall(html):
            cc=_jra_norm_cname(cc)
            if ("pw01dde10" in cc and _jra_date_from_cname(cc)==date and
                _jra_track_from_cname(cc)==track and _jra_race_no_from_cname(cc)==race_no):
                live.append(cc)
        if live:
            cname=live[0]
            try: html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,0)
            except Exception:pass
    soup=BeautifulSoup(html,"html.parser")
    full=_jra_text(soup)
    if not date or not track or not race_no:return None
    start=jra_start_time(full)
    course_desc,_=jra_course(full)
    distance=jra_distance(full)
    surface=jra_surface(full)
    environment=_parse_jra_environment_html(full,surface)
    weather=environment.get("weather") or "不明"
    condition=environment.get("condition") or "不明"
    title=jra_race_title(soup,race_no,JRA_BAD_TITLE_RE)
    race_grade,race_class=jra_grade_class(full)
    prize1=jra_first_prize(full)
    horses=[]
    withdrawn_entries=[]
    target_table=select_jra_runners_table(soup)
    if not target_table:return None
    for tr in target_table.find_all("tr"):
        cells=tr.find_all(["th","td"])
        if len(cells)<4:continue
        # horse number among first 3 cells
        no,noidx=jra_runner_row_number(cells,_jra_text)
        if not no:
            marker=tr.select_one('td.num')
            status=_scratch_status(_jra_text(marker))
            name_tag=tr.select_one('td.horse .name a')
            if status and name_tag:
                withdrawn_entries.append({'name':_jra_text(name_tag),'horseNumber':None,
                    '_jraHorseCname':_jra_attr_cname(name_tag,JRA_HORSE_CNAME_RE),
                    'status':status,'scratched':True,'sourceHorseNumberMissing':True})
            continue
        frame_no=0
        fm=re.search(r"枠\s*(\d)",_jra_text(cells[0])+" "+str(cells[0]))
        if fm:frame_no=int(fm.group(1))
        # identify horse info and profile cells
        info=None; profile=None; horse_cname=""
        for c in cells:
            hc=_jra_attr_cname(c,JRA_HORSE_CNAME_RE)
            if hc:
                info=c;horse_cname=hc;break
        if info is None:
            info=cells[min(len(cells)-1,noidx+1)]
        info_i=cells.index(info)
        profile=cells[info_i+1] if info_i+1<len(cells) else None
        # horse name from horse profile link or first plausible link/text
        name=""
        for a in info.find_all("a"):
            if _jra_attr_cname(a,JRA_HORSE_CNAME_RE):
                name=_jra_text(a);break
        if not name:
            name=re.split(r"\d+(?:\.\d+)?\(?",_jra_text(info),1)[0].strip()[:40]
        if not name:continue
        infot=_jra_text(info); prot=_jra_text(profile)
        sex="";age=0
        sx=re.search(r"(牡|牝|せん)(\d+)",prot)
        if sx:sex=sx.group(1);age=int(sx.group(2))
        cw=0.0
        cwm=re.search(r"(\d{2}(?:\.\d)?)\s*kg",prot)
        if cwm:cw=float(cwm.group(1))
        jockey=""
        links=[_jra_text(a) for a in profile.find_all("a")] if profile else []
        if links:jockey=links[-1]
        if not jockey and cwm:
            jockey=prot[cwm.end():].strip().split(" ")[0:3]
            jockey=" ".join(jockey).strip()
        trainer_tag=info.select_one('p.trainer a')
        trainer=_jra_text(trainer_tag)
        affiliation=observed_affiliation(_jra_text(info.select_one('p.trainer')))
        tm=re.search(r"([^\s]+(?:\s[^\s]+)?)\s*\((?:美浦|栗東|本会外)\)",infot)
        if not trainer and tm:trainer=tm.group(1).strip()
        prize=0
        prm=re.search(r"([\d,.]+)万円",infot)
        if prm:
            try:prize=int(float(prm.group(1).replace(",",""))*10000)
            except:pass
        past=[]
        past_cells=cells[info_i+2:info_i+6]
        for c in past_cells:
            rr=_jra_parse_past_cell(c,date)
            if rr:past.append(rr)
        # JRA card exposes 前走〜4走前. If all four slots were inspected and fewer
        # than four real runs exist, that is the horse's full career to date.
        career_complete=(len(past_cells)>=4 and len(past)<4)
        win_odds=0.0; popularity=0; body_weight=0; body_change=None
        tail=infot.split(name,1)[1] if name in infot else infot
        om=re.search(r"([0-9]+(?:\.[0-9]+)?)\s*\((\d+)番人気\)",tail)
        if om:
            try: win_odds=float(om.group(1)); popularity=int(om.group(2))
            except: pass
        bwm=re.search(r"(\d{3})\s*kg\s*[（(]\s*([+\-]?\d+)\s*[）)]",infot)
        if bwm:
            try: body_weight=int(bwm.group(1)); body_change=int(bwm.group(2))
            except: pass
        elif re.search(r"(\d{3})\s*kg",infot):
            try: body_weight=int(re.search(r"(\d{3})\s*kg",infot).group(1))
            except: pass
        scratch_status=_scratch_status(_jra_text(tr))
        horses.append({"horseNumber":no,"frameNumber":frame_no,"name":name,"age":age,"sex":sex,"carriedWeight":cw,"jockey":jockey,"trainer":trainer,"affiliation":affiliation,"prizeMoneyAtRace":prize,"recentRaces":past,"winOdds":win_odds or None,"popularity":popularity or None,"bodyWeight":body_weight or None,"bodyWeightChange":body_change,"oddsSource":"JRA公式" if win_odds else "","status":scratch_status,"scratched":bool(scratch_status),"_jraHorseCname":horse_cname,"_jraCareerComplete":career_complete,"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}})
    if not horses:return None
    program=_jra_program_lookup(date,track,race_no)
    if program:title=program.get("title") or title;distance=int(program.get("distance") or distance);surface=program.get("surface") or surface;start=program.get("startTime") or start
    # Listing must stay fast. Full five-run profile supplementation is done only when needed.
    if supplement_profiles:
        def supplement(h):
            existing=h.get("recentRaces") or []
            if _jra_history_complete(existing,bool(h.get("_jraCareerComplete"))):return h
            extra=_jra_profile_runs(h.get("_jraHorseCname") or "",date,5)
            h["recentRaces"]=_jra_merge_runs(existing,extra,5)
            return h
        workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            horses=list(pool.map(supplement,horses))
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"raceGrade":race_grade,"raceClass":race_class,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":jra_race_field_size(horses),"racePrize1":prize1,"startTime":start,"scheduledStartTime":start,"horses":horses,"withdrawnEntries":withdrawn_entries,"source":"JRA公式","jraCname":cname})

def _jra_parse_race_summary(cname:str)->dict|None:
    """Fast list-page parser: no horse/profile parsing. Full card loads only when opened."""
    date=_jra_date_from_cname(cname); track=_jra_track_from_cname(cname); race_no=_jra_race_no_from_cname(cname)
    if not date or not track or not race_no:return None
    cache_sec=45 if date==_today_iso() else 900
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",cname,cache_sec)
    except Exception:return None
    soup=BeautifulSoup(html,"html.parser"); full=_jra_text(soup)
    start=jra_start_time(full)
    distance=jra_distance(full)
    surface=jra_surface(full)
    environment=_parse_jra_environment_html(full,surface)
    weather=environment.get("weather") or "不明"
    condition=environment.get("condition") or "不明"
    title=jra_race_title(soup,race_no,JRA_BAD_TITLE_RE)
    race_grade,race_class=jra_grade_class(full)
    program=_jra_program_lookup(date,track,race_no)
    if program:title=program.get("title") or title;distance=int(program.get("distance") or distance);surface=program.get("surface") or surface;start=program.get("startTime") or start
    rid=f"jra-{date}-{track}-{race_no:02d}"
    return normalize_central_race({"id":rid,"date":date,"track":track,"raceNumber":race_no,"title":title,"raceGrade":race_grade,"raceClass":race_class,"distance":distance,"surface":surface,"condition":condition,"weather":weather,"fieldSize":0,"racePrize1":0,"startTime":start,"scheduledStartTime":start,"horses":[],"source":"JRA公式・高速一覧","jraCname":cname,"_summaryOnly":True})

def fetch_jra_official(iso_date:str, lightweight: bool = False)->list[dict]:
    if lightweight:return _jra_program_summaries(iso_date)
    token=iso_date.replace("-","")
    try:
        home=_jra_request("https://www.jra.go.jp/",None,120)
    except Exception:
        return []
    seeds=[]
    for c in JRA_CNAME_RE.findall(home):
        if token in c and c not in seeds:
            seeds.append(c)
    if not seeds:
        return []

    # v48: a race page contains links to the other active venue(s) too.
    # v47 filtered those links to the first venue, which could leave only Nakayama.
    # Discover one seed per track first, then expand each venue to all race-number links.
    track_seed={}
    for c in seeds:
        tr=_jra_track_from_cname(c)
        if tr and tr not in track_seed:
            track_seed[tr]=c

    discovered=[]
    processed_tracks=set()
    queue=list(track_seed.items())
    guard=0
    while queue and guard<12:
        guard+=1
        track,seed=queue.pop(0)
        if track in processed_tracks:
            continue
        processed_tracks.add(track)
        try:
            html=_jra_request("https://www.jra.go.jp/JRADB/accessD.html",seed,180)
        except Exception:
            continue
        links=[]
        for c in JRA_CNAME_RE.findall(html):
            if token not in c:
                continue
            if c not in links:
                links.append(c)
            if c not in discovered:
                discovered.append(c)
        # Important: do NOT restrict to the current track. Any newly linked venue
        # becomes a seed and is expanded on its own page.
        for c in links:
            tr=_jra_track_from_cname(c)
            if tr and tr not in processed_tracks and all(q[0]!=tr for q in queue):
                queue.append((tr,c))

    for c in seeds:
        if c not in discovered:
            discovered.append(c)

    # prefer detailed 01 variant and deduplicate by venue/race number
    chosen=_choose_race_cards(discovered,_jra_track_from_cname,_jra_race_no_from_cname)

    def one(c):
        try:
            return _jra_parse_race_summary(c) if lightweight else _jra_parse_race(c, supplement_profiles=True)
        except Exception as exc:
            print("JRA official race parse failed",c,exc)
            return None
    workers=max(4,min(16,int(os.getenv("JRA_SUMMARY_WORKERS","12") if lightweight else os.getenv("JRA_RACE_WORKERS","6"))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        races=[x for x in pool.map(one,chosen.values()) if x]
    races.sort(key=lambda r:(r.get("track") or "",int(r.get("raceNumber") or 0)))
    return races

def _jra_any_track(cname:str)->str:
    m=re.search(r"pw01(?:d|s)de(?:01|10)(\d{2})",cname or "",re.I)
    return JRA_TRACK_CODES.get(m.group(1),"") if m else ""

def _jra_any_race_no(cname:str)->int:
    m=re.search(r"pw01(?:d|s)de(?:01|10)\d{2}\d{4}\d{4}(\d{2})20\d{6}/",cname or "",re.I)
    return int(m.group(1)) if m else 0

def _jra_parse_result(result_cname:str,base:dict|None=None, *, strict_errors: bool = False)->dict|None:
    if not result_cname:return None
    try:html=_jra_request("https://www.jra.go.jp/JRADB/accessS.html",result_cname,20)
    except Exception as exc:
        if strict_errors:raise
        print("JRA official result fetch failed",result_cname,exc);return None
    return _parse_jra_result_html(
        html, result_cname, base, date_from_cname=_jra_date_from_cname,
        track_from_cname=_jra_any_track, race_no_from_cname=_jra_any_race_no,
        parse_time_seconds=_jra_parse_time_seconds, parse_payouts=_parse_payouts,
        bad_title_re=JRA_BAD_TITLE_RE, text=_jra_text, clean=_clean)
