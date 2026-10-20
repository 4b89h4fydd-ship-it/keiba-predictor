"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _precompute_detail_metrics(detail: dict) -> dict:
    detail = prepare_race_detail(detail)
    if not isinstance(detail,dict):return detail
    detail=_apply_enrichment(str(detail.get("id") or ""),detail)
    try:detail["trackSpeed"]=_pc_live_track_speed(detail)
    except Exception:detail["trackSpeed"]={"version":"track-speed-v300","score":0.5,"ratio":1.0,"evidence":0.0,"completed":0,"label":"基準","source":"fallback"}
    for horse in detail.get("horses",[]) or []:
        runs=horse.get("allPastRuns") or horse.get("recentRaces") or []
        from arvexq.career_missing import build_career_analysis
        verified_no_starts = (detail.get("analysisMode") == "新馬" and
            build_career_analysis(horse,detail).get("career_state") == "complete-no-starts")
        if verified_no_starts:
            horse["debutNoHistory"]=True
        else:
            horse.pop("debutNoHistory",None)
        horse["collectionState"]={"status":"complete" if runs or horse.get("debutNoHistory") else "basic" if horse.get("name") else "missing", "history":"not_applicable" if horse.get("debutNoHistory") and not runs else "available" if runs else "missing", "pastRunCount":len(runs)}
        metric_horse=dict(horse,recentRaces=[r for r in runs if _is_jump_run(r)]) if detail.get("analysisMode")=="障害" else dict(horse,recentRaces=runs)
        try:
            sectional,sectional_n=_pc_sectional_score(metric_horse,detail)
            if sectional is not None:
                horse["officialSectionalScore"]=round(sectional,6)
                horse["officialSectionalSamples"]=sectional_n
                # Prefer the reproducible past-run sectional signal over an opaque supplied lap score.
                horse["lapScore"]=round(sectional,6)
        except Exception:
            pass
        # JRA/NAR use one observed 60/40 scorer; never call the retired
        # synthetic integrated evaluation for either circuit.
        horse["integratedEvaluation"] = {}
        try:
            horse["precomputedMetrics"]={"style":_pc_style_metrics(metric_horse,detail),"fit":_pc_fit_metrics(metric_horse,detail),"sectional":{"score":horse.get("officialSectionalScore"),"samples":horse.get("officialSectionalSamples",0)}}
        except Exception:
            horse.setdefault("precomputedMetrics",{})
    # Prediction, marks and betting recommendations are retired.
    for horse in detail.get("horses", []) or []:
        horse.pop("integratedEvaluation", None)
    detail.pop("aiEvaluation", None)
    detail.pop("factorRanking", None)
    detail.pop("honmeiDecision", None)
    detail.pop("volatility", None)
    detail.setdefault("preparedMeta",{})["metricsPrecomputed"]=True
    return detail

def _fast_local_race_detail(race_id:str)->dict|None:
    """First paint from local DB only. Never wait on web/history/profile lookups."""
    now=int(time.time())
    if race_id.startswith("nar-"):
        m=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-(.+)-(\d{2})$",race_id)
        if not m or not DB_PATH.exists():return None
        iso_date,track,race_no=m.group(1),m.group(2),int(m.group(3))
        conn=_new_conn(DB_PATH)
        try:
            race=conn.execute("SELECT * FROM races WHERE track=? AND date=? AND race_no=?",(track,iso_date,race_no)).fetchone()
            if not race:return None
            entries=conn.execute("SELECT * FROM entries WHERE track=? AND date=? AND race_no=? ORDER BY horse_no",(track,iso_date,race_no)).fetchall()
        finally:conn.close()
        if not entries:return None
        horses=[];finishers=[]
        for e in entries:
            horses.append({"id":_stable_id(iso_date,track,race_no,e["horse_no"],e["name"]),
                "horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),"name":e["name"],
                "age":int(e["age"] or 0),"sex":e["sex"] or "","carriedWeight":float(e["carried_weight"] or 0),
                "jockey":e["jockey"] or "","trainer":e["trainer"] or "",
                "status":str(e["status"] or "") if "status" in e.keys() else "",
                "scratched":bool(_scratch_status(str(e["status"] or ""))) if "status" in e.keys() else False,
                "recentRaces":[],
                "jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{},
                "collectionState":{"status":"basic","history":"loading","pastRunCount":0}})
            fin=int(e["finish"] or 0)
            if fin>0:
                try:cp=json.loads(e["corner_positions_json"] or "[]")
                except Exception:cp=[]
                finishers.append({"finish":fin,"horseNumber":int(e["horse_no"]),"frameNumber":int(e["frame_no"] or 0),
                                  "name":e["name"],"timeSeconds":float(e["time_seconds"] or 0),"cornerPositions":cp})
        finishers.sort(key=lambda x:(x["finish"],x["horseNumber"]))
        need=min(3,len(entries));ranks={x["finish"] for x in finishers}
        finalized=need>0 and all(i in ranks for i in range(1,need+1))
        detail={"id":race_id,"circuit":"地方","date":iso_date,"track":track,"raceNumber":race_no,
                "title":race["title"] or f"{race_no}R","distance":int(race["distance"] or 0),
                "condition":race["condition"] or "不明","weather":race["weather"] or "不明",
                "fieldSize":int(race["field_size"] or len(entries)),"racePrize1":int(race["prize1"] or 0),
                "surface":"","startTime":race["start_time"] or "",
                "scheduledStartTime":race["scheduled_start_time"] or race["start_time"] or "",
                "horses":horses,"result":{"status":"確定","finishers":finishers} if finalized else None,
                "source":"NAR公式・高速Snapshot"}
    else:
        if not CENTRAL_DB_PATH.exists():return None
        conn=_new_conn(CENTRAL_DB_PATH)
        try:row=conn.execute("SELECT payload FROM central_races WHERE id=?",(race_id,)).fetchone()
        finally:conn.close()
        if not row:return None
        try:detail=json.loads(row["payload"])
        except Exception:return None
        if not isinstance(detail,dict) or not (detail.get("horses") or []):return None
        detail=dict(detail);detail["id"]=race_id
        for h in detail.get("horses",[]) or []:
            if not isinstance(h,dict):continue
            runs=list(h.get("recentRaces") or h.get("allPastRuns") or [])[:5]
            h["recentRaces"]=runs;h.pop("allPastRuns",None)
            h.setdefault("jockeyStats",{});h.setdefault("trainerStats",{})
            h.setdefault("jockeyProfile",{});h.setdefault("trainerProfile",{})
            h["collectionState"]={"status":"complete" if runs else "basic",
                                  "history":"available" if runs else "loading","pastRunCount":len(runs)}
        detail["source"]=str(detail.get("source") or "JRA")+"・高速Snapshot"
    try:
        latest=RACEDB.odds_latest(race_id);by={int(x.get("horseNumber") or 0):x for x in latest}
        for h in detail.get("horses",[]) or []:
            z=by.get(int(h.get("horseNumber") or 0))
            if z:
                if z.get("winOdds") is not None:h["winOdds"]=z["winOdds"]
                if z.get("popularity") is not None:h["popularity"]=z["popularity"]
    except Exception:pass
    title=str(detail.get("title") or "");surface=str(detail.get("surface") or "")
    detail["analysisMode"]="障害" if (surface=="障害" or "障害" in title or "ジャンプ" in title) else ("新馬" if re.search(r"(?:新馬|メイクデビュー)",title) else "平地")
    try:
        saved_analysis=RACEDB.get_analysis(race_id)
        if saved_analysis:detail["analysis"]=saved_analysis
    except Exception:pass
    detail["preparedMeta"]={"prepared":True,"fastPartial":True,"preparedAtEpoch":now,"build":"v93-fast"}
    return detail

def _build_fast_diagnosis_snapshot(race_id:str, allow_network:bool=False, deep_context:bool=False)->dict|None:
    """Recalculate all-horse diagnosis from local data only. Target: sub-second."""
    # Preserve current-card/result fields already hydrated by the fast-card step.
    # v156 rebuilt from the bare local NAR DB here and immediately erased body weights/results.
    detail=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if detail:
        detail=json.loads(json.dumps(detail,ensure_ascii=False,default=str))
    if not detail:return None
    if race_id.startswith("nar-"):
        detail=_nar_attach_recent_batch(detail,5)
    else:
        for h in detail.get("horses",[]) or []:
            h["recentRaces"]=list(h.get("recentRaces") or [])[:5]

    # Merge every locally stored historical start before computing diagnosis.
    detail=_attach_stored_career(detail)
    detail=_apply_enrichment(race_id,detail)

    quality=_diagnosis_history_quality(detail)
    if allow_network and not race_id.startswith("nar-") and not quality.get("ready") and detail.get("analysisMode")!="新馬":
        # Background/prewarm only: one page contains up to 5 previous starts for every runner.
        detail=_merge_fast_history(detail,_netkeiba_past_rows_fast(detail))
        detail=_attach_stored_career(detail)
        quality=_diagnosis_history_quality(detail)

    detail=_strip_excluded(detail)
    if deep_context:detail=_attach_evaluation_context(detail)
    detail=_precompute_detail_metrics(detail)
    detail=_restore_saved_odds(detail)
    quality=_diagnosis_history_quality(detail)

    pm=detail.setdefault("preparedMeta",{})
    pm.pop("fastPartial",None)
    pm["diagnosisVersion"]=PREDICTION_ENGINE_VERSION
    pm["diagnosisReady"]=bool(quality.get("ready"))
    pm["diagnosisPreparedAtEpoch"]=time.time()
    pm["diagnosisCoverage"]=quality
    detail["historySearch"]={
        "status":"local-ready" if quality.get("ready") else "history-loading",
        "monthsDone":0,"maxMonths":0,
        "coverage":{
            "totalHorses":quality.get("total",0),
            "totalRuns":quality.get("runs",0),
            "horsesWithHistory":quality.get("withHistory",0),
        },
        "error":"","source":"RaceDB + 一括5走履歴"
    }
    try:
        RACEDB.upsert_race(detail)
        _schedule_full_history_harvest(detail)
    except Exception as exc:print("fast diagnosis RaceDB save failed",race_id,exc)
    try:PREPARED_STORE.put(detail,force=True)
    except Exception as exc:print("fast diagnosis prepared save failed",race_id,exc)
    return _compact_display_snapshot(detail)

def _store_fast_snapshot(detail:dict)->None:
    if not detail or not _racedb_snapshot_usable(detail):return
    detail=_restore_saved_odds(detail)
    try:PREPARED_STORE.put(detail,force=True)
    except Exception as exc:print("fast prepared save failed",detail.get("id"),exc)
    try:RACEDB.upsert_race(detail)
    except Exception as exc:print("fast RaceDB save failed",detail.get("id"),exc)

@app.post("/api/v1/racedb/analysis/{race_id}")
async def racedb_save_analysis(race_id: str, request: Request):
    try:
        payload=await request.json()
        if not isinstance(payload,dict):raise ValueError("invalid analysis payload")
        payload["raceId"]=race_id
        cached=_prepared_get_fresh(race_id)
        if cached and (cached.get("date")!=_today_iso() or _snapshot_final(cached)):
            return {"ok":True,"raceId":race_id,"stored":False,"frozen":True}
        RACEDB.save_analysis(race_id,payload)
        if cached:
            cached["analysis"]=payload
            PREPARED_STORE.put(cached)
        return {"ok":True,"raceId":race_id,"stored":True}
    except Exception as exc:
        raise HTTPException(status_code=400,detail=str(exc))
