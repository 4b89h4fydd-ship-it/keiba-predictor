"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _schedule_live_refresh(iso_date: str, force: bool = False):
    key = f"live:{iso_date}"
    now = int(time.time())
    with _live_refresh_lock:
        if key in _live_refresh_running or (not force and now - _live_refresh_last.get(key, 0) < 90):
            return
        _live_refresh_running.add(key)
    def worker():
        changed=False
        try:
            try:
                target = datetime.strptime(iso_date, "%Y-%m-%d").date()
                sync = NarSync()
                with _nar_sync_io_lock:
                    if iso_date == _today_iso():
                        sync.sync_daily(force=force)
                    else:
                        # Target only the selected month instead of a bulk history crawl.
                        sync.sync_month(target.year,target.month,force=force)
                changed=True
            except Exception as exc:
                print(f"NAR background sync failed: {exc}")
            if changed:
                # v48: an empty list may have been cached before the async NAR fetch finished.
                with _race_list_cache_lock:
                    [_race_list_cache.pop(k,None) for k in list(_race_list_cache) if k.startswith(iso_date+"|")]
        finally:
            with _live_refresh_lock:
                _live_refresh_running.discard(key)
                _live_refresh_last[key] = int(time.time())
    threading.Thread(target=worker, daemon=True).start()

def _schedule_central_refresh(iso_date: str, force: bool = False):
    now=int(time.time())
    with _central_refresh_lock:
        if iso_date in _central_refresh_running:
            return
        # current day can refresh frequently; older dates are effectively immutable
        ttl=90 if iso_date==_today_iso() else 3600
        if not force and now-_central_refresh_last.get(iso_date,0)<ttl:
            return
        _central_refresh_running.add(iso_date)
    def worker():
        success=False
        try:
            if _clean(os.getenv("CENTRAL_FEED_URL", "")):
                rows=fetch_central_feed(iso_date)
            else:
                rows=fetch_jra_official(iso_date, lightweight=True)
                if not rows: rows=_netkeiba_race_summaries(iso_date)
            if rows:
                st=CentralStore()
                try: st.upsert(rows)
                finally: st.conn.close()
                success=True
                with _race_list_cache_lock:
                    [_race_list_cache.pop(k,None) for k in list(_race_list_cache) if k.startswith(iso_date+"|")]
        except Exception as exc:
            print(f"Central async refresh failed: {exc}")
        finally:
            with _central_refresh_lock:
                _central_refresh_running.discard(iso_date)
                # Successful fetches use the normal TTL. Empty/failed fetches retry quickly.
                _central_refresh_last[iso_date]=int(time.time()) if success else max(0,int(time.time())-85)
    threading.Thread(target=worker,daemon=True).start()

def _commercial_collect_once():
    started=time.time()
    with _commercial_collector_lock:
        if _commercial_collector_state["running"]:return
        _commercial_collector_state.update({"running":True,"lastStart":started,"lastError":"","hydrated":0,"diagnosed":0})
    queued=ready=0;errs=[]
    try:
        today=_today_iso()
        _schedule_live_refresh(today,False)
        _schedule_central_refresh(today,False)
        # Short settle only; the next cycle catches anything still downloading.
        time.sleep(float(os.getenv("COMMERCIAL_LIST_SETTLE_SEC","1.2")))
        rows=[]
        try:rows.extend(nar_race_summaries(today))
        except Exception as exc:errs.append("NAR list: "+str(exc))
        try:rows.extend(central_race_summaries(today,allow_network=False))
        except Exception as exc:errs.append("JRA list: "+str(exc))
        nowj=_now_jst();now_min=nowj.hour*60+nowj.minute
        targets=_commercial_target_rows(rows,now_min)
        for idx,r in enumerate(targets):
            rid=str(r.get("id") or "")
            if not rid:continue
            d=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
            pm=(d or {}).get("preparedMeta") or {}
            if d and pm.get("diagnosisVersion")==PREDICTION_ENGINE_VERSION and pm.get("diagnosisReady"):
                ready+=1;continue
            # Upcoming races first, but all jobs share the same two-worker queue.
            priority=20+idx
            _schedule_fast_card_refresh(rid,priority);queued+=1
        with _race_list_cache_lock:_race_list_cache.clear()
        _schedule_day_bundle_refresh(today,False)
    except Exception as exc:errs.append(str(exc))
    finally:
        finished=time.time()
        with _commercial_collector_lock:
            _commercial_collector_state.update({
                "running":False,"lastFinish":finished,"lastError":" | ".join(errs[-6:]),
                "hydrated":ready,"diagnosed":ready,"queued":queued,"cycleSec":round(finished-started,2),
            })

def _commercial_collector_loop():
    first_delay=float(os.getenv("COMMERCIAL_COLLECTOR_START_DELAY_SEC","1.0"))
    interval=max(120,int(os.getenv("COMMERCIAL_COLLECTOR_INTERVAL_SEC","180")))
    time.sleep(first_delay)
    while True:
        try:_commercial_collect_once()
        except Exception as exc:print("commercial collector cycle failed",exc)
        time.sleep(interval)

@app.on_event("startup")
def _start_commercial_collector():
    enabled=str(os.getenv("ARVEXQ_COMMERCIAL_COLLECTOR","1")).lower() in {"1","true","yes","on"}
    if enabled:
        threading.Thread(target=_commercial_collector_loop,daemon=True,name="arvexq-commercial-collector").start()

def _data_core_cycle():
    global _data_core_state
    with _data_core_lock:
        if _data_core_state.get("running"):return
        _data_core_state.update({"running":True,"lastStart":int(time.time()),"checked":0,"refreshed":0,"error":""})
    checked=refreshed=0;errors=[]
    try:
        rows=_data_core_day_rows(_today_iso())
        nowj=_now_jst();nowm=nowj.hour*60+nowj.minute
        candidates=[]
        for r in rows:
            rid=str(r.get("id") or "")
            if not rid:continue
            d=_data_core_snapshot(rid);h=_data_core_health(d);checked+=1
            _data_core_store_health(d,set(),"local") if d else None
            needed=[k for k in ("card","history","odds","body_weight","environment","analysis") if h.get(k,{}).get("status") not in {"ready","not_due"}]
            if _data_core_result_due(d or r) and h.get("result",{}).get("status")!="ready":needed.append("result")
            if h.get("result",{}).get("status")=="ready" and h.get("payouts",{}).get("status")!="ready":needed.append("payouts")
            if needed:
                st=_race_minutes_server(r);dist=abs(st-nowm) if st<9999 else 9999
                candidates.append((dist,st,rid,needed))
        candidates.sort(key=lambda x:(x[0],x[1]))
        targets=candidates[:max(1,int(os.getenv("ARVEXQ_DATA_CORE_BATCH","16")))]
        workers=max(1,min(8,len(targets))) if targets else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for z in pool.map(lambda x:_data_core_refresh_race(x[2],False),targets):
                    refreshed+=1
                    if not z.get("ok") and z.get("errors"):errors.extend(z.get("errors") or [])
    except Exception as exc:errors.append(str(exc))
    finally:
        with _data_core_lock:
            _data_core_state.update({"running":False,"lastFinish":int(time.time()),"checked":checked,"refreshed":refreshed,"error":" | ".join(errors[-5:])})

def _data_core_loop():
    time.sleep(float(os.getenv("ARVEXQ_DATA_CORE_START_DELAY_SEC","1.2")))
    while True:
        try:_data_core_cycle()
        except Exception as exc:print("ARVEXQ Data Core cycle failed",exc)
        time.sleep(max(10,int(os.getenv("ARVEXQ_DATA_CORE_LOOP_SEC","12"))))

@app.on_event("startup")
def _start_data_core_collector():
    enabled=str(os.getenv("ARVEXQ_DATA_CORE","1")).lower() in {"1","true","yes","on"}
    if enabled:threading.Thread(target=_data_core_loop,daemon=True,name="arvexq-data-core").start()

def _racedb_live_cycle()->None:
    today=_today_iso();rows=[]
    _schedule_live_refresh(today,False)
    _schedule_central_refresh(today,False)
    try:rows.extend(nar_race_summaries(today))
    except Exception as exc:print("RaceDB NAR list failed",exc)
    try:rows.extend(central_race_summaries(today,allow_network=True,force=False))
    except Exception as exc:print("RaceDB JRA list failed",exc)
    if rows:_schedule_prewarm(rows,today,"")
    # Odds are much more volatile than past runs.  Only poll a few upcoming races.
    if not bool(int(os.getenv("RACEDB_AUTO_ODDS","1"))):return
    nowm=_now_jst().hour*60+_now_jst().minute;window=int(os.getenv("RACEDB_ODDS_WINDOW_MIN","90"));limit=max(1,int(os.getenv("RACEDB_ODDS_MAX_RACES","4")))
    upcoming=[]
    for r in rows:
        if r.get("result"):continue
        t=str(r.get("startTime") or "")
        m=re.match(r"^(\d{1,2}):(\d{2})",t)
        if not m:continue
        rm=int(m.group(1))*60+int(m.group(2));delta=rm-nowm
        if -5<=delta<=window:upcoming.append((delta,r))
    upcoming.sort(key=lambda x:x[0])
    for _,r in upcoming[:limit]:
        try:odds_refresh(str(r.get("id") or ""))
        except Exception as exc:print("RaceDB automatic odds failed",r.get("id"),exc)

def _start_racedb_daemon()->None:
    global _racedb_daemon_started
    if str(os.getenv("ARVEXQ_COMMERCIAL_COLLECTOR","1")).lower() in {"1","true","yes","on"}:return
    if not bool(int(os.getenv("RACEDB_AUTO_UPDATE","1"))):return
    with _racedb_daemon_lock:
        if _racedb_daemon_started:return
        _racedb_daemon_started=True
    def worker():
        # Short initial delay lets app import/route registration finish.
        time.sleep(float(os.getenv("RACEDB_START_DELAY_SEC","2")))
        while True:
            try:_racedb_live_cycle()
            except Exception as exc:print("RaceDB live cycle failed",exc)
            time.sleep(max(30,int(os.getenv("RACEDB_UPDATE_SEC","120"))))
    threading.Thread(target=worker,daemon=True,name="RaceDB-live-updater").start()
