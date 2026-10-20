"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/volatility-pack")
def volatility_pack(date: str = Query(...), circuit: str = Query(...), track: str = Query(...)):
    """All 1R-12R upset labels from local DB only. Designed for sub-second venue paint."""
    key=f"{date}|{circuit}|{track}"
    now=time.time()
    with _volatility_pack_lock:
        hit=_volatility_pack_cache.get(key)
        if hit and now-hit[0]<8:
            return {"date":date,"circuit":circuit,"track":track,"races":hit[1],"cached":True}

    try:
        summaries=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
    except Exception:
        summaries=[]
    targets=[r for r in summaries if str(r.get("track") or "")==str(track) and r.get("id")]
    targets.sort(key=lambda r:int(r.get("raceNumber") or 0))

    existing=_local_volatility_map([str(r.get("id") or "") for r in targets])
    items=[]
    for r in targets:
        rid=str(r.get("id") or "")
        v=existing.get(rid)
        if not v or not v.get("ready"):
            v=_compute_local_volatility_for_race(rid) or v
        items.append({
            "id":rid,
            "raceNumber":int(r.get("raceNumber") or 0),
            "volatility":v or {
                "version":VOLATILITY_ENGINE_VERSION,"ready":False,
                "score":None,"label":"…","method":"pre-race/no-odds",
                "oddsUsed":False,"reasons":["評価材料を収集中"]
            }
        })

    with _volatility_pack_lock:
        _volatility_pack_cache[key]=(now,items)
        if len(_volatility_pack_cache)>40:
            oldest=min(_volatility_pack_cache.items(),key=lambda kv:kv[1][0])[0]
            _volatility_pack_cache.pop(oldest,None)
    return {"date":date,"circuit":circuit,"track":track,"races":items,"cached":False}

@app.post("/api/v1/race/{race_id}/diagnosis-refresh")
def diagnosis_refresh(race_id: str):
    """Local-only diagnosis refresh. External history is prepared by the queue."""
    cached=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if cached:
        pm=cached.get("preparedMeta") or {}
        if pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION and pm.get("diagnosisReady"):
            return {
                "status":"done","raceId":race_id,"engineVersion":PREDICTION_ENGINE_VERSION,
                "race":_compact_display_snapshot(cached),"cached":True,
            }
    snap=_build_fast_diagnosis_snapshot(race_id,allow_network=False)
    if not snap:
        return JSONResponse(status_code=202,content={"status":"preparing","raceId":race_id})
    ready=bool((snap.get("preparedMeta") or {}).get("diagnosisReady"))
    return {
        "status":"done" if ready else "preparing",
        "raceId":race_id,
        "engineVersion":PREDICTION_ENGINE_VERSION,
        "race":_compact_display_snapshot(snap),
        "cached":False,
    }

@app.get("/api/v1/racedb/analysis/{race_id}")
def racedb_get_analysis(race_id: str):
    return {"raceId":race_id,"analysis":RACEDB.get_analysis(race_id)}
