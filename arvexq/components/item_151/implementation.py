"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.post("/api/v1/central-ingest")
async def central_ingest(request: Request):
    expected = _clean(os.getenv("CENTRAL_INGEST_TOKEN", ""))
    if not expected:
        raise HTTPException(status_code=503, detail="CENTRAL_INGEST_TOKEN is not configured")
    supplied = _clean(request.headers.get("X-Ingest-Token", ""))
    if supplied != expected:
        raise HTTPException(status_code=401, detail="invalid ingest token")
    body = await request.json()
    rows = body if isinstance(body, list) else body.get("races", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="races must be a list")
    count = CentralStore().upsert(rows)
    return {"status":"ok","stored":count}

def _data_core_day_rows(date:str)->list[dict]:
    try:return _bootstrap_rows_local(date)
    except Exception:return []

def _data_core_day_status(date:str,circuit:str="")->dict:
    rows=[r for r in _data_core_day_rows(date) if not circuit or str(r.get("circuit") or "")==str(circuit)]
    ids=[str(r.get("id") or "") for r in rows if r.get("id")]
    by={rid:{} for rid in ids}
    if ids:
        conn=sqlite3.connect(RACEDB.path,timeout=3);conn.row_factory=sqlite3.Row
        try:
            marks=",".join("?" for _ in ids)
            for r in conn.execute(f"SELECT * FROM field_state WHERE race_id IN ({marks})",ids).fetchall():
                by.setdefault(str(r["race_id"]),{})[str(r["field_key"])]=dict(r)
        finally:conn.close()
    fields={k:{"ready":0,"partial":0,"missing":0,"pending":0,"not_due":0} for k in DATA_CORE_FIELDS}
    ready_races=0
    race_rows=[]
    for r in rows:
        rid=str(r.get("id") or "");st=by.get(rid) or {}
        # If not yet persisted, calculate from the latest local snapshot without network.
        if not st:
            h=_data_core_health(_data_core_snapshot(rid))
            st={k:{"status":v.get("status"),"completeness":v.get("completeness"),"source":v.get("source"),"note":v.get("note")} for k,v in h.items()}
        for k in DATA_CORE_FIELDS:
            status=str((st.get(k) or {}).get("status") or "missing")
            fields[k][status if status in fields[k] else "missing"]+=1
        essential=("card","history","odds","body_weight","environment","analysis")
        ready=all(str((st.get(k) or {}).get("status") or "") in ({"ready","not_due"} if k in {"odds","body_weight"} else {"ready"}) for k in essential)
        if ready:ready_races+=1
        race_rows.append({"id":rid,"track":r.get("track"),"raceNumber":r.get("raceNumber"),"startTime":r.get("startTime"),"ready":ready,"fields":st})
    return {"version":ARVEXQ_DATA_CORE_VERSION,"date":date,"circuit":circuit,"raceCount":len(rows),"readyRaceCount":ready_races,"fields":fields,"races":race_rows}

@app.post("/api/v1/data-core/refresh/{race_id}")
def data_core_refresh(race_id:str,force:int=Query(1)):
    if race_id.startswith("nar-") and any(f"-{name}-" in race_id for name in ("帯広", "帯広ば")):
        raise HTTPException(status_code=404,detail="race venue excluded")
    return _data_core_refresh_race(race_id,bool(force))

@app.post("/api/v1/data-core/refresh-day")
def data_core_refresh_day(date:str=Query(""),circuit:str=Query("")):
    ds=date or _today_iso();rows=[r for r in _data_core_day_rows(ds) if (not circuit or str(r.get("circuit") or "")==str(circuit)) and str(r.get("track") or "") not in ("帯広", "帯広ば")]
    # Queue the full day without keeping the request open; the status endpoint exposes progress.
    def worker():
        ordered=sorted(rows,key=lambda r:_race_minutes_server(r))
        for r in ordered:
            rid=str(r.get("id") or "")
            if rid:
                try:_data_core_refresh_race(rid,True)
                except Exception as exc:print("data core day refresh failed",rid,exc)
    threading.Thread(target=worker,daemon=True,name="data-core-day-"+ds).start()
    return {"status":"queued","date":ds,"circuit":circuit,"raceCount":len(rows),"version":ARVEXQ_DATA_CORE_VERSION}

def _prewarm_sort_key(row: dict, date: str) -> tuple:
    t=str(row.get("startTime") or "")
    try:
        hh,mm=t.split(":",1);m=int(hh)*60+int(mm[:2])
    except Exception:
        m=9999
    if date==_today_iso():
        now=_now_jst().hour*60+_now_jst().minute
        return (0 if m>=now else 1, m if m>=now else m+1440, str(row.get("track") or ""), int(row.get("raceNumber") or 0))
    return (0,m,str(row.get("track") or ""),int(row.get("raceNumber") or 0))

def _schedule_prewarm(rows: list[dict], date: str, circuit: str = "") -> None:
    ordered=[r for r in sorted(rows,key=lambda x:_prewarm_sort_key(x,date)) if r.get("id") and (not circuit or r.get("circuit")==circuit)]
    max_races=max(1,int(os.getenv("PREWARM_MAX_RACES","36")))
    ordered=ordered[:max_races]
    if not ordered:return
    key=f"{date}|{circuit or 'all'}"
    with _prewarm_lock:
        if key in _prewarm_running:return
        _prewarm_running.add(key);_prewarm_state[key]={"running":True,"done":0,"total":len(ordered),"last":int(time.time()),"errors":0}
    def worker():
        done=errs=0
        workers=max(1,min(int(os.getenv("PREWARM_WORKERS","2")),len(ordered)))
        deep=max(0,int(os.getenv("PREWARM_DEEP_RACES","3")))
        def one(ix_row):
            ix,row=ix_row;rid=str(row.get("id") or "")
            detail=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
            if detail:
                if not (_prepared_get_fresh(rid) or _racedb_get_fast(rid)):_store_fast_snapshot(detail)
            else:
                _schedule_fast_card_refresh(rid)
            return rid,detail
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures=[pool.submit(one,x) for x in enumerate(ordered)]
                for fut in as_completed(futures):
                    try:
                        _,detail=fut.result()
                        if detail:done+=1
                        else:errs+=1
                    except Exception as exc:
                        errs+=1;print("prewarm failed",exc)
                    with _prewarm_lock:_prewarm_state[key]={"running":True,"done":done,"total":len(ordered),"last":int(time.time()),"errors":errs}
        finally:
            with _prewarm_lock:
                _prewarm_running.discard(key);_prewarm_state[key]={"running":False,"done":done,"total":len(ordered),"last":int(time.time()),"errors":errs}
    threading.Thread(target=worker,daemon=True).start()

def _local_starter_bundle(rows:list[dict], limit:int=3)->list[dict]:
    if not rows:return []
    ordered=sorted(
        [r for r in rows if r.get("id")],
        key=lambda r:(str(r.get("track") or ""),int(r.get("raceNumber") or 0))
    )
    first_track=str(ordered[0].get("track") or "") if ordered else ""
    candidates=[r for r in ordered if str(r.get("track") or "")==first_track][:limit]
    out=[]
    for r in candidates:
        rid=str(r.get("id") or "")
        d=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
        if d and (d.get("horses") or []):
            out.append(_compact_display_snapshot(d))
    return out

@app.post("/api/v1/prewarm-track")
def prewarm_track(date: str = Query(...), circuit: str = Query(...), track: str = Query(...), race_no: int = Query(1)):
    rows=[]
    try:rows=(nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False))
    except Exception:rows=[]
    all_targets=sorted(
        [r for r in rows if str(r.get("track") or "")==str(track) and r.get("id") and str(r.get("track") or "") not in ("帯広", "帯広ば")],
        key=lambda r:abs(int(r.get("raceNumber") or 0)-int(race_no))
    )
    near=all_targets[:3];rest=all_targets[3:]
    queued=0
    for idx,r in enumerate(near+rest):
        rid=str(r["id"])
        local=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
        pm=(local or {}).get("preparedMeta") or {}
        v=(local or {}).get("volatility") or {}
        current=pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION and pm.get("diagnosisReady") and v.get("version")==VOLATILITY_ENGINE_VERSION
        if not local or not current:
            priority=(10+idx*10) if idx<3 else (90+idx)
            _schedule_fast_card_refresh(rid,priority);queued+=1
    return {"status":"started","count":len(all_targets),"queued":queued,"mode":"nearest-3-plus-background"}
