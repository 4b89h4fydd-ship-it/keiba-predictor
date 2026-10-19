"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

class DayBundleStore:
    def __init__(self,path:Path):
        self.path=path
        self.path.parent.mkdir(parents=True,exist_ok=True)
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS day_bundles(
                race_date TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                complete INTEGER NOT NULL DEFAULT 0,
                race_count INTEGER NOT NULL DEFAULT 0,
                detail_count INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            )""")
            conn.commit()
        finally:conn.close()

    def get(self,race_date:str,complete_only:bool=False)->dict|None:
        conn=sqlite3.connect(self.path,timeout=3);conn.row_factory=sqlite3.Row
        try:
            sql="SELECT * FROM day_bundles WHERE race_date=?"
            args=[race_date]
            if complete_only:sql+=" AND complete=1"
            row=conn.execute(sql,args).fetchone()
            if not row:return None
            try:p=json.loads(row["payload"])
            except Exception:return None
            p["persisted"]=True
            p["updatedAtEpoch"]=int(row["updated_at"] or 0)
            p["complete"]=bool(row["complete"])
            p["raceCount"]=int(row["race_count"] or 0)
            p["detailCount"]=int(row["detail_count"] or 0)
            return p
        finally:conn.close()

    def put(self,race_date:str,payload:dict,complete:bool)->None:
        if not race_date or not isinstance(payload,dict):return
        conn=sqlite3.connect(self.path,timeout=5)
        try:
            conn.execute("""INSERT INTO day_bundles(race_date,payload,complete,race_count,detail_count,updated_at)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(race_date) DO UPDATE SET
                              payload=excluded.payload,complete=excluded.complete,
                              race_count=excluded.race_count,detail_count=excluded.detail_count,
                              updated_at=excluded.updated_at""",
                         (race_date,json.dumps(payload,ensure_ascii=False,separators=(",",":"),default=str),
                          1 if complete else 0,int(payload.get("raceCount") or 0),
                          int(payload.get("detailCount") or 0),int(time.time())))
            conn.commit()
        finally:conn.close()

def _bootstrap_rows_local(date:str)->list[dict]:
    raw=races(date,"",0,0)
    rows=raw.get("races",[]) if isinstance(raw,dict) else list(raw or [])
    out=[];seen=set()
    for r in rows:
        rid=str(r.get("id") or "")
        if not rid or rid in seen:continue
        seen.add(rid);out.append(r)
    out.sort(key=lambda r:(str(r.get("circuit") or ""),str(r.get("track") or ""),int(r.get("raceNumber") or 0)))
    return out

def _bootstrap_sources_running(date:str)->bool:
    running=False
    try:
        with _live_refresh_lock:
            running=running or (f"live:{date}" in _live_refresh_running)
    except Exception:pass
    try:
        running=running or bool(_central_refresh_status(date).get("running"))
    except Exception:pass
    return bool(running)

def _bootstrap_display_ready(d:dict|None)->bool:
    """Enough data to open/render the race immediately."""
    if not isinstance(d,dict):return False
    return bool((d.get("horses") or []) or d.get("result"))

def _bootstrap_analysis_ready(d:dict|None)->bool:
    """Diagnosis readiness is tracked separately and must never block site display."""
    if not _bootstrap_display_ready(d):return False
    if _snapshot_final(d):return True
    pm=d.get("preparedMeta") or {}
    return bool(pm.get("diagnosisReady") and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION)

def _bootstrap_detail_ready(d:dict|None)->bool:
    return _bootstrap_display_ready(d)

def _bootstrap_detail_local(race_id:str,force_hydrate:bool=False)->dict|None:
    """Fast local snapshot for day bundles. Heavy diagnosis work is background-only."""
    d=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if not d:
        try:d=_fast_local_race_detail(race_id)
        except Exception:d=None
    if not d:
        if force_hydrate:_schedule_fast_card_refresh(race_id,5)
        return None
    d=_restore_saved_odds(d)
    if os.getenv("ARVEXQ_COLLECT_ONLY","0")!="1":
        d=_ensure_race_volatility(d)
    if force_hydrate and os.getenv("ARVEXQ_COLLECT_ONLY","0")!="1" and not _bootstrap_analysis_ready(d):_schedule_fast_card_refresh(race_id,8)
    return _compact_display_snapshot(d)

def _assemble_day_bundle(date:str,allow_network_fill:bool=False)->dict:
    rows=_bootstrap_rows_local(date)
    details=[]
    if rows:
        workers=max(1,min(8,int(os.getenv("DAY_BUNDLE_WORKERS","6")),len(rows)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures={
                pool.submit(_bootstrap_detail_local,str(r.get("id")),allow_network_fill):str(r.get("id"))
                for r in rows
            }
            for fut in as_completed(futures):
                try:d=fut.result()
                except Exception as exc:
                    print("day bundle race failed",futures[fut],exc);d=None
                if d and d.get("id"):details.append(d)

    details.sort(key=lambda d:(str(d.get("circuit") or ""),str(d.get("track") or ""),int(d.get("raceNumber") or 0)))
    display_ids={str(d.get("id") or "") for d in details if _bootstrap_display_ready(d)}
    analysis_ids={str(d.get("id") or "") for d in details if _bootstrap_analysis_ready(d)}
    missing=[str(r.get("id") or "") for r in rows if str(r.get("id") or "") not in display_ids]
    source_running=_bootstrap_sources_running(date)
    display_complete=bool(rows) and not missing and not source_running

    return {
        "date":date,"races":rows,"details":details,
        "raceCount":len(rows),"detailCount":len(display_ids),
        "analysisCount":len(analysis_ids),
        "missing":missing,
        "complete":display_complete,
        "displayComplete":display_complete,
        "analysisComplete":bool(rows) and len(analysis_ids)>=len(rows),
        "sourceRunning":source_running,
        "generatedAtEpoch":int(time.time()),
        "source":"nonblocking-day-bundle"
    }

def _refresh_day_bundle(date:str,force_sources:bool=False,wait_for_complete:bool=False,timeout_sec:float=25.0)->dict:
    """Single-pass bundle refresh. Missing/outdated races are queued and never block the caller."""
    started=time.time()
    with _site_bootstrap_build_lock:
        with _site_bootstrap_lock:
            _site_bootstrap_state[date]={"running":True,"startedAt":int(started),"raceCount":0,"ready":0,"missing":[]}
        if force_sources or date==_today_iso():
            try:_schedule_live_refresh(date,force=bool(force_sources))
            except Exception:pass
            try:_schedule_central_refresh(date,force=bool(force_sources))
            except Exception:pass
        payload=_assemble_day_bundle(date,allow_network_fill=False)
        missing=list(payload.get("missing") or [])
        for rid in missing:_schedule_fast_card_refresh(rid,5)
        if os.getenv("ARVEXQ_COLLECT_ONLY","0")!="1":
            for d in payload.get("details") or []:
                if d and d.get("id") and not _bootstrap_analysis_ready(d):_schedule_fast_card_refresh(str(d.get("id")),12)
        try:DAY_BUNDLES.put(date,payload,bool(payload.get("displayComplete")))
        except Exception:pass
        with _site_bootstrap_lock:
            _site_bootstrap_cache[date]=(time.time(),payload)
            _site_bootstrap_state[date]={
                "running":False,"startedAt":int(started),"finishedAt":int(time.time()),
                "raceCount":int(payload.get("raceCount") or 0),"ready":int(payload.get("detailCount") or 0),
                "analysisReady":int(payload.get("analysisCount") or 0),"missing":missing,
                "sourceRunning":bool(payload.get("sourceRunning")),"elapsedMs":int((time.time()-started)*1000),
            }
        return payload

def _schedule_day_bundle_refresh(date:str,force_sources:bool=False)->None:
    with _site_bootstrap_lock:
        st=_site_bootstrap_state.get(date) or {}
        if st.get("running"):return
        _site_bootstrap_state[date]={"running":True,"startedAt":int(time.time()),"raceCount":0,"ready":0,"missing":[]}
    def worker():
        try:_refresh_day_bundle(date,force_sources,True,float(os.getenv("DAY_BUNDLE_BUILD_TIMEOUT_SEC","45")))
        except Exception as exc:
            print("day bundle refresh failed",date,exc)
            with _site_bootstrap_lock:
                st=dict(_site_bootstrap_state.get(date) or {})
                st.update({"running":False,"error":str(exc),"finishedAt":int(time.time())})
                _site_bootstrap_state[date]=st
    threading.Thread(target=worker,daemon=True,name="day-bundle-"+date).start()

def _site_bootstrap_payload(date:str,force:bool=False,wait:bool=False)->dict:
    """
    Customer path is strictly non-blocking.
    Return the best local bundle immediately, then continue full preparation in background.
    v240: a fresh force=1 collector result must not be immediately replaced by an
    older persisted bundle on the next non-force poll.
    """
    stored=DAY_BUNDLES.get(date,complete_only=True)
    recent_force=None
    with _site_bootstrap_lock:
        fc=_site_force_cache.get(date)
        if fc and time.time()-float(fc[0])<=60:
            recent_force=dict(fc[1])
    if not force and recent_force and (not stored or _bundle_quality(recent_force)>=_bundle_quality(stored)):
        out=dict(recent_force)
        out["cached"]=False
        out["servedFrom"]="recent-force-live"
        return out
    if stored and not force:
        if date==_today_iso() and int(time.time())-int(stored.get("updatedAtEpoch") or 0)>20:
            _schedule_day_bundle_refresh(date,False)
        out=dict(stored)
        out["cached"]=True
        out["servedFrom"]="persistent-display-complete"
        return out

    # Local-only assembly: no external fetch and no waiting for the builder lock.
    try:
        current=_assemble_day_bundle(date,allow_network_fill=False)
    except Exception as exc:
        print("nonblocking bootstrap assemble failed",date,exc)
        current={"date":date,"races":[],"details":[],"raceCount":0,"detailCount":0,
                 "analysisCount":0,"missing":[],"complete":False,
                 "displayComplete":False,"analysisComplete":False,
                 "sourceRunning":False,"generatedAtEpoch":int(time.time()),
                 "source":"nonblocking-day-bundle"}

    # Persist a complete display bundle; analysis may still improve later.
    if current.get("displayComplete"):
        try:DAY_BUNDLES.put(date,current,True)
        except Exception:pass

    # Always kick the expensive work into background.
    _schedule_day_bundle_refresh(date,bool(force))

    current["cached"]=False
    current["servedFrom"]="local-immediate"
    return current

def _force_day_live_snapshot(date:str, timeout_sec:float=23.0)->dict:
    """GitHub collector path: all-card live fields first, diagnosis second.

    v304 refreshed each race as one long job (card -> odds -> result -> diagnosis).
    Slow diagnosis jobs could occupy all workers and starve later races before their
    odds call ever started.  v305 splits the phases: every race gets an odds attempt
    first; only then do we spend the remaining budget on results/diagnosis.
    """
    started=time.time()
    try:_schedule_live_refresh(date,force=True)
    except Exception:pass
    try:_schedule_central_refresh(date,force=True)
    except Exception:pass
    deadline=started+max(8.0,float(timeout_sec))
    # Let program/card discovery start, but reserve most of the request for market data.
    while time.time()<deadline and _bootstrap_sources_running(date):
        if time.time()-started>2.2:break
        time.sleep(.15)
    rows=_bootstrap_rows_local(date)
    if not rows:
        return _site_bootstrap_payload(date,True,False)

    def snapshot(rid:str)->dict:
        return _prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid) or {}

    def live_coverage(d:dict)->tuple[int,int,int]:
        hs=[h for h in (d.get("horses") or []) if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
        got=sum(1 for h in hs if float(h.get("winOdds") or 0)>0)
        weights=sum(1 for h in hs if int(h.get("bodyWeight") or 0)>250)
        return len(hs),got,weights

    # PHASE 1 — FULL CARD ODDS. No diagnosis is allowed to block these workers.
    def market_one(row):
        rid=str(row.get("id") or "")
        if not rid:return rid,False
        try:
            d=snapshot(rid)
            if not _bootstrap_display_ready(d):
                try:_hydrate_fast_card_now(rid,deep_history=False)
                except Exception as exc:print("full-day card hydrate failed",rid,exc)
            body=odds_refresh(rid,1)
            field=int((body or {}).get("fieldCount") or 0);got=int((body or {}).get("oddsCount") or 0)
            return rid,bool(field and got==field)
        except Exception as exc:
            print("full-day market refresh failed",rid,exc)
            return rid,False

    market_workers=max(6,min(int(os.getenv("FULL_DAY_ODDS_WORKERS","20")),24,len(rows)))
    market_results={}
    ex=ThreadPoolExecutor(max_workers=market_workers)
    futures={ex.submit(market_one,r):str(r.get("id") or "") for r in rows}
    # Reserve a few seconds for a second sparse-row pass and bundle assembly.
    market_deadline=min(deadline-5.0,time.time()+max(6.0,min(14.0,deadline-time.time()-5.0)))
    try:
        done,_=wait(list(futures),timeout=max(.5,market_deadline-time.time()))
        for fut in done:
            rid=futures[fut]
            try:market_results[rid]=bool(fut.result()[1])
            except Exception:market_results[rid]=False
    finally:
        ex.shutdown(wait=False,cancel_futures=True)

    # PHASE 1B — retry only races still missing at least one active runner's odds.
    missing=[]
    for r in rows:
        rid=str(r.get("id") or "")
        field,got,_=live_coverage(snapshot(rid))
        if rid and field and got<field:missing.append(r)
    if missing and time.time()<deadline-2.5:
        retry_workers=max(4,min(int(os.getenv("FULL_DAY_ODDS_RETRY_WORKERS","16")),20,len(missing)))
        ex=ThreadPoolExecutor(max_workers=retry_workers)
        fs=[ex.submit(market_one,r) for r in missing]
        try:wait(fs,timeout=max(.5,min(4.0,deadline-time.time()-2.0)))
        finally:ex.shutdown(wait=False,cancel_futures=True)

    # In the canonical facts-first Actions job this endpoint is discovery only.
    # Official results have their own writer and diagnosis runs after D1 readback.
    collect_only=os.getenv("ARVEXQ_COLLECT_ONLY","0")=="1"
    # PHASE 2 — legacy interactive live updates, never the collector stage.
    nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
    focus=[]
    for r in rows:
        st=_race_minutes_server(r)
        remain=(st-nowm) if st<9999 else 9999
        if (-45<=remain<=240) or not _bootstrap_analysis_ready(snapshot(str(r.get("id") or ""))):
            focus.append(r)
    focus.sort(key=lambda r:abs((_race_minutes_server(r) if _race_minutes_server(r)<9999 else nowm+9999)-nowm))
    focus=[] if collect_only else focus[:max(12,min(28,len(focus)))]

    def finish_one(row):
        rid=str(row.get("id") or "")
        if not rid:return None
        try:
            st=_race_minutes_server(row)
            if st<9999 and nowm>=st+2 and not _snapshot_final(snapshot(rid)):
                try:_refresh_result_fast(rid)
                except Exception:pass
            # Rebuild only after live fields have been persisted, so newly published
            # body weight can affect the current diagnosis without starving market fetches.
            try:_build_fast_diagnosis_snapshot(rid,allow_network=False,deep_context=False)
            except Exception as exc:print("focused diagnosis rebuild failed",rid,exc)
            d=snapshot(rid)
            return _compact_display_snapshot(d) if d else None
        except Exception as exc:
            print("focused live rebuild failed",rid,exc)
            return None

    if focus and time.time()<deadline-1.2:
        workers=max(4,min(10,len(focus)))
        ex=ThreadPoolExecutor(max_workers=workers)
        fs=[ex.submit(finish_one,r) for r in focus]
        try:wait(fs,timeout=max(.4,deadline-time.time()-1.0))
        finally:ex.shutdown(wait=False,cancel_futures=True)

    out=_assemble_day_bundle(date,allow_network_fill=False)
    if out.get("displayComplete"):
        try:DAY_BUNDLES.put(date,out,True)
        except Exception:pass
    dc_ready=0
    for d in out.get("details",[]) or []:
        try:
            hh=_data_core_store_health(d,set(),"force-day")
            if all((hh.get(k) or {}).get("status")=="ready" for k in ("card","history","odds","body_weight","environment","analysis")):
                dc_ready+=1
        except Exception as exc:print("data core force health failed",(d or {}).get("id"),exc)
    out["dataCore"]={"version":ARVEXQ_DATA_CORE_VERSION,"readyRaceCount":dc_ready,"raceCount":len(out.get("races") or [])}
    odds_ready=0;odds_partial=0;odds_missing=[]
    for d in out.get("details",[]) or []:
        hs=[h for h in (d.get("horses") or []) if not h.get("scratched") and int(h.get("horseNumber") or 0)>0]
        got=sum(1 for h in hs if float(h.get("winOdds") or 0)>0)
        if hs and got==len(hs):odds_ready+=1
        elif hs and got:odds_partial+=1;odds_missing.append(str(d.get("id") or ""))
        elif hs:odds_missing.append(str(d.get("id") or ""))
    out["oddsReadyCount"]=odds_ready
    out["oddsPartialCount"]=odds_partial
    out["oddsMissingRaceIds"]=odds_missing
    out["forceLiveRefresh"]=True
    out["forceElapsedMs"]=int((time.time()-started)*1000)
    with _site_bootstrap_lock:
        _site_force_cache[date]=(time.time(),dict(out))
        _site_bootstrap_cache[date]=(time.time(),dict(out))
    return out

@app.get("/api/v1/site-bootstrap")
def site_bootstrap(date: str = Query(...), force: int = Query(0), wait: int = Query(0)):
    """Fast customer bootstrap; force=1 is the GitHub full-day collector path."""
    if force:
        try:return _force_day_live_snapshot(date,23.0)
        except Exception as exc:
            print("force day snapshot failed",date,exc)
    return _site_bootstrap_payload(date,False,False)

def _site_bootstrap_warm_loop():
    time.sleep(float(os.getenv("BOOTSTRAP_START_DELAY_SEC","2.5")))
    while True:
        try:_schedule_day_bundle_refresh(_today_iso(),False)
        except Exception as exc:print("bundle warmer failed",exc)
        time.sleep(max(20,int(os.getenv("BOOTSTRAP_REFRESH_SEC","30"))))

@app.on_event("startup")
def _start_site_bootstrap_warmer():
    enabled=str(os.getenv("ARVEXQ_BOOTSTRAP_WARM","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_site_bootstrap_warm_loop,daemon=True,name="arvexq-bootstrap").start()
