"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def nar_race_detail(race_id: str) -> dict | None:
    m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
    if not m:return None
    iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
    store=NarStore()
    try:
        race=store.conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
        if not race:return None
        entries=store.conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        horses=[]
        for e in entries:
            horses.append({
                "id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),"horseNumber":int(e["horse_no"]),
                "frameNumber":int(e["frame_no"] or 0),"name":e["name"],"age":int(e["age"] or 0),"sex":e["sex"] or "",
                "carriedWeight":float(e["carried_weight"] or 0),"jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "status":str(e["status"] or "") if "status" in e.keys() else "",
                "scratched":bool(_scratch_status(str(e["status"] or ""))) if "status" in e.keys() else False,
                "jockeyStats":store.stats("jockey",e["jockey"],iso_date),"trainerStats":store.stats("trainer",e["trainer"],iso_date),
                "jockeyProfile":store.role_profile("jockey",e["jockey"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "trainerProfile":store.role_profile("trainer",e["trainer"],iso_date,track,int(race["distance"] or 0),race["condition"] or "不明"),
                "prizeMoneyAtRace":store.prize_before(e["name"],iso_date),"recentRaces":store.recent_races(e["name"],iso_date,5),
            })
        finishers=[]
        for e in entries:
            fin=int(e["finish"] or 0)
            if entries:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"] or 999,x["horseNumber"]))
        need=min(3,len(entries)); ranks={x["finish"] for x in finishers}; finalized=need>0 and all(i in ranks for i in range(1,need+1))
        detail={"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),"condition":race["condition"] or "不明",
                "weather":race["weather"] or "不明","fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "","scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "startTimeChanged":bool((race["scheduled_start_time"] or "") and (race["start_time"] or "") and race["scheduled_start_time"]!=race["start_time"]),
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,"source":"NAR公式"}
        return detail
    finally:
        try:store.conn.close()
        except Exception:pass

def central_race_detail(race_id: str) -> dict | None:
    detail=None
    if CENTRAL_DB_PATH.exists():
        conn=_new_conn(CENTRAL_DB_PATH)
        try:
            row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
            if row:
                try:detail=json.loads(row["payload"])
                except Exception as exc:print("central payload decode failed",race_id,exc)
        finally:conn.close()
    if detail is None:
        mm=re.match(r"^jra-(20\d{2}-\d{2}-\d{2})-([^\-]+)-(\d{2})$",str(race_id or ""))
        if mm:
            detail=_jra_program_lookup(mm.group(1),mm.group(2),int(mm.group(3)))
            if detail:
                detail["id"]=race_id
                try:st=CentralStore();st.upsert([detail]);st.conn.close()
                except Exception as exc:print("central fallback cache save failed",exc)
    if detail is None:return None
    date=str(detail.get("date") or "");track=str(detail.get("track") or "");race_no=int(detail.get("raceNumber") or 0)
    program=_jra_program_lookup(date,track,race_no)
    if program:
        for k in ("title","distance","surface","startTime","scheduledStartTime","meetingNumber","meetingDay","netkeibaRaceId"):
            v=program.get(k)
            if v not in (None,"",0):detail[k]=v
    if not detail.get("netkeibaRaceId"):detail["netkeibaRaceId"]=_netkeiba_program_race_id(date,track,race_no)
    cname=str(detail.get("jraCname") or "")
    should_result=_race_should_have_result(detail)
    if not cname and (should_result or not (detail.get("horses") or []) or int(detail.get("distance") or 0)<=0):
        cname=_jra_find_cname(date,track,race_no)
        if cname:detail["jraCname"]=cname
    # Finished race: fetch JRA official result first. This also supplies exact weather/going.
    if should_result and cname:
        try:
            rc=str(detail.get("resultCname") or "") or _jra_result_cname_from_card(cname)
            if rc:
                official=_jra_parse_result(rc,detail)
                if official:detail=_merge_official_result(detail,official)
        except Exception as exc:print("JRA official result hydrate failed",race_id,exc)
    # Official JRA card is primary for the pre-race card and live body data.
    malformed=(not (detail.get("horses") or []) or bool(JRA_BAD_TITLE_RE.search(str(detail.get("title") or ""))) or int(detail.get("distance") or 0)<=0)
    if cname:
        try:
            live=_jra_parse_race(cname,supplement_profiles=False)
            if live:
                if malformed:
                    # Keep any official result already obtained, but replace the card with the official entry data.
                    saved_result=detail.get("result");saved_rc=detail.get("resultCname")
                    detail=live
                    if saved_result:detail["result"]=saved_result
                    if saved_rc:detail["resultCname"]=saved_rc
                else:
                    for k in ("title","distance","surface","condition","weather","fieldSize","startTime","scheduledStartTime"):
                        v=live.get(k)
                        if v not in (None,"",0,"不明"):detail[k]=v
                    by_no={int(h.get("horseNumber") or 0):h for h in live.get("horses",[]) or []}
                    for h in detail.get("horses",[]) or []:
                        z=by_no.get(int(h.get("horseNumber") or 0))
                        if z:
                            for k in ("bodyWeight","bodyWeightChange","sex","age","carriedWeight","jockey","trainer"):
                                if z.get(k) not in (None,"",0,[]):h[k]=z.get(k)
                            if z.get("recentRaces"):
                                h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],z.get("recentRaces") or [],5)
        except Exception as exc:print("JRA official card hydrate failed",race_id,exc)
    # If the official card is unavailable (e.g. publication ended), fill missing card rows from netkeiba.
    if not (detail.get("horses") or []):
        try:
            nr=_netkeiba_detail_rows(detail)
            if nr:
                for h in nr:
                    h.pop("winOdds",None);h.pop("popularity",None);h.pop("oddsSource",None)
                detail["horses"]=nr;detail["fieldSize"]=len(nr);detail.setdefault("dataSources",[])
                if "netkeiba" not in detail["dataSources"]:detail["dataSources"].append("netkeiba")
        except Exception as exc:print("central card fallback failed",race_id,exc)
    # Before official results exist, fill only missing weather/going from a secondary public race page.
    if detail.get("condition") in (None,"","不明") or detail.get("weather") in (None,"","不明"):
        try:
            meta=_netkeiba_race_meta(detail)
            for k in ("title","distance","condition","weather","startTime"):
                if detail.get(k) in (None,"",0,"不明") and meta.get(k) not in (None,"",0,"不明"):detail[k]=meta[k]
        except Exception as exc:print("central race meta fallback failed",race_id,exc)
    # Result fallback only if JRA official result link was not available yet.
    if should_result and not (detail.get("result") and (detail.get("result") or {}).get("finishers")):
        try:
            rr=_netkeiba_current_result(detail)
            if rr:
                for f in rr.get("finishers",[]) or []:f.pop("winOdds",None)
                detail["result"]=rr
                # Populate result/body fields without odds.
                hs=detail.get("horses") or [];by_no={int(h.get("horseNumber") or 0):h for h in hs}
                for f in rr.get("finishers",[]) or []:
                    h=by_no.get(int(f.get("horseNumber") or 0))
                    if h:
                        for k in ("bodyWeight","bodyWeightChange"):
                            if f.get(k) not in (None,""):h[k]=f.get(k)
        except Exception as exc:print("central result fallback failed",race_id,exc)
    detail.pop("oddsSource",None);detail.pop("oddsType",None);detail.pop("oddsUpdatedAt",None)
    for h in detail.get("horses",[]) or []:
        h.pop("winOdds",None);h.pop("popularity",None);h.pop("oddsSource",None)
    if detail.get("horses") or detail.get("result"):
        try:st=CentralStore();st.upsert([detail]);st.conn.close()
        except Exception as exc:print("central hydrated cache save failed",exc)
    cutoff=str(detail.get("date") or "9999-12-31")
    for h in detail.get("horses",[]) or []:
        try:
            stored=_central_recent_from_store(str(h.get("name") or ""),cutoff,5)
            h["recentRaces"]=_merge_central_recent(h.get("recentRaces") or [],stored,cutoff,5)
        except Exception as exc:
            print("central horse history merge failed",race_id,h.get("name"),exc)
            h["recentRaces"]=[x for x in (h.get("recentRaces") or []) if isinstance(x,dict)][:5]
    return detail

@app.get("/api/v1/race/{race_id}")
def race_detail(race_id: str, refresh: int = Query(0), history: int = Query(1), prepared: int = Query(1), view: str = Query("")):
    # v3 factual opt-in on the existing route; no additional provider/refresh.
    if view == "v3-facts":
        from arvexq.v3.transport.fastapi_readonly import saved_fact_screen
        try:
            projection = saved_fact_screen(
                race_id, lambda requested_id:
                _prepared_get_fresh(requested_id) or _racedb_get_fast(requested_id)
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if projection is None:
            return JSONResponse(status_code=404, content={
                "status": "not-in-existing-cache", "raceId": race_id})
        return projection
    cached=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if cached:
        if race_id.startswith("nar-") and str(cached.get("date") or "")==_today_iso():
            hs=[h for h in cached.get("horses",[]) or [] if not h.get("scratched")]
            weights=sum(1 for h in hs if int(h.get("bodyWeight") or 0)>250)
            weight_missing=bool(hs) and weights<max(1,math.ceil(len(hs)*.80))
            result_missing=_nar_result_should_be_available(cached) and not _snapshot_final(cached)
            if refresh or weight_missing or result_missing:_schedule_fast_card_refresh(race_id,0)
        return _compact_display_snapshot(cached)
    quick=_fast_local_race_detail(race_id)
    if quick:
        _store_fast_snapshot(quick)
        return _compact_display_snapshot(quick)
    _schedule_fast_card_refresh(race_id,0)
    return JSONResponse(status_code=202,content={"status":"preparing","raceId":race_id})

@app.get("/api/v1/racedb-race/{race_id}")
def racedb_race(race_id:str):
    detail,updated=RACEDB.get_race(race_id)
    if not detail:raise HTTPException(status_code=404,detail="RaceDB snapshot not found")
    return {"updatedAt":updated,"detail":detail,"oddsLatest":RACEDB.odds_latest(race_id)}
