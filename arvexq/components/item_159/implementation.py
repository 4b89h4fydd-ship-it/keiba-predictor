"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _prepare_race_snapshot(race_id: str, force: bool = False, manual: bool = False) -> dict | None:
    hit=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if hit and (str(hit.get("date") or "")<_today_iso() or _snapshot_final(hit)) and not force:return hit
    if hit and not force:return hit
    if manual and race_id.startswith("nar-"):
        match=re.match(r"^nar-(\d{4}-\d{2}-\d{2})-",race_id)
        if match:
            target=datetime.strptime(match.group(1),"%Y-%m-%d")
            sync=NarSync()
            try:
                with _nar_sync_io_lock:
                    if match.group(1)==_today_iso():sync.sync_daily(force=True)
                    else:sync.sync_month(target.year,target.month,force=True)
            finally:sync.store.conn.close()
    detail=nar_race_detail(race_id) if race_id.startswith("nar-") else central_race_detail(race_id)
    if not detail:return None
    horses=detail.get("horses") if isinstance(detail.get("horses"),list) else []
    if not race_id.startswith("nar-") and int(detail.get("fieldSize") or 0)>0 and not horses and not detail.get("result"):
        return None
    if race_id.startswith("nar-"):detail=_attach_nar_payouts(detail)
    if hit and hit.get("analysis"):detail["analysis"]=hit["analysis"]
    detail=_strip_excluded(_apply_enrichment(race_id,detail))
    detail=_attach_stored_career(detail)
    # This canonical provider path is also used in the standalone fact stage.
    # AI evaluation is deferred until facts have been written and read from D1.
    if os.getenv("ARVEXQ_COLLECT_ONLY","0") != "1":
        detail=_precompute_detail_metrics(_attach_evaluation_context(detail))
    detail=_restore_saved_odds(detail)
    detail.setdefault("preparedMeta",{}).pop("fastPartial",None)
    # Snapshot creation never blocks on network history. Existing DB/feed history is included.
    detail.setdefault("historySearch",{"status":"prepared","monthsDone":0,"maxMonths":0,"coverage":{"totalHorses":len(detail.get("horses",[])),"totalRuns":sum(len(h.get("recentRaces") or []) for h in detail.get("horses",[]))},"error":"","source":detail.get("source") or "prepared"})
    try:
        RACEDB.upsert_race(detail)
        _schedule_full_history_harvest(detail)
    except Exception as exc:print("RaceDB snapshot write failed",race_id,exc)
    PREPARED_STORE.put(detail,force=bool(manual or force))
    display=_compact_display_snapshot(detail)
    if detail.get("date")==_today_iso() and not _snapshot_final(detail):_schedule_detail_background_jobs(race_id,detail)
    return display

def _ensure_detail_background_jobs(race_id: str, detail: dict) -> None:
    if detail.get("date")!=_today_iso() or _snapshot_final(detail):return
    try:
        es=_enrichment_status(race_id)
        if es.get("status") in {"idle","unavailable"}:_start_enrichment(race_id,detail)
    except Exception as exc:
        print("prepared enrichment schedule failed",race_id,exc)
    try:
        if race_id.startswith("nar-"):
            names=[str(h.get("name") or "") for h in detail.get("horses",[]) if h.get("name")]
            cov=_history_counts(names,detail.get("date") or "9999-12-31")
            if _race_history_status(race_id) is None and not _history_is_enough(cov,0):_start_race_history_search(race_id,detail.get("date") or _today_iso(),names)
        else:
            cov=_central_detail_coverage(detail);total=int(cov.get("totalHorses") or 0);resolved=int(cov.get("horsesResolved") or cov.get("horsesWith5Plus") or 0)
            if detail.get("analysisMode")!="新馬" and _race_history_status(race_id) is None and not assess_career_readiness(detail).get("ready"):_start_central_history_search(race_id,detail.get("date") or _today_iso())
    except Exception as exc:
        print("prepared history schedule failed",race_id,exc)

def _schedule_detail_background_jobs(race_id: str, detail: dict) -> None:
    threading.Thread(target=_ensure_detail_background_jobs,args=(race_id,detail),daemon=True).start()

def _ensure_fast_card_workers():
    global _fast_card_workers_started
    with _fast_card_cv:
        if _fast_card_workers_started:return
        _fast_card_workers_started=True
        workers=max(1,min(6,int(os.getenv("FAST_CARD_WORKERS","4"))))
        for idx in range(workers):
            threading.Thread(target=_fast_card_worker,daemon=True,name=f"fast-card-worker-{idx+1}").start()

def _queue_fast_card(race_id:str,priority:int=50):
    if not race_id:return
    _ensure_fast_card_workers()
    with _fast_card_cv:
        if race_id in _fast_card_pending or race_id in _fast_card_running:return
        _fast_card_pending.add(race_id)
        _fast_card_queue.append((int(priority),time.time(),race_id))
        _fast_card_queue.sort(key=lambda x:(x[0],x[1]))
        _fast_card_cv.notify()

def _fast_card_worker():
    while True:
        with _fast_card_cv:
            while not _fast_card_queue:_fast_card_cv.wait()
            priority,_,race_id=_fast_card_queue.pop(0)
            _fast_card_pending.discard(race_id)
            _fast_card_running.add(race_id)
        try:
            deep=priority<=10
            _hydrate_fast_card_now(race_id,deep_history=deep)
            if os.getenv("ARVEXQ_COLLECT_ONLY","0")!="1":
                try:_build_fast_diagnosis_snapshot(race_id,allow_network=False,deep_context=deep)
                except Exception as exc:print("fast diagnosis after card failed",race_id,exc)
        except Exception as exc:
            print("fast card worker failed",race_id,exc)
        finally:
            with _fast_card_cv:_fast_card_running.discard(race_id)

@app.post("/api/v1/prepare-race/{race_id}")
def prepare_race(race_id:str):
    """Queue the selected race first; customer HTTP request returns immediately."""
    _schedule_fast_card_refresh(race_id,0)
    return {"status":"queued","raceId":race_id,"priority":0}
