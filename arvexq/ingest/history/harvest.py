"""history/harvest: original PR #13 acquisition orchestration.

Storage, evaluation and provider callbacks are explicit keyword-only ports.
Worker behavior, source priority and immutable prediction handling are preserved.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import threading
import time



from arvexq.ingest.history.jobs import _full_history_lock
from arvexq.ingest.history.jobs import _full_history_running

def _schedule_full_history_harvest(detail: dict, *, NarStore, PREPARED_STORE, RACEDB, _attach_evaluation_context, _attach_stored_career, _jra_profile_runs, _precompute_detail_metrics, _today_iso) -> None:
    """Persist every career run exposed by the currently available official source without blocking the race screen."""
    if not bool(int(os.getenv("RACEDB_FULL_HISTORY","1"))) or not isinstance(detail,dict):return
    # Historical/final cards also need pre-race career data for backtests.
    # Source functions receive the race-date cutoff, so later races are excluded.
    if not detail.get("date"):return
    race_id=str(detail.get("id") or "");horses=[h for h in (detail.get("horses") or []) if isinstance(h,dict) and h.get("name")]
    if not race_id or not horses:return
    with _full_history_lock:
        if race_id in _full_history_running:return
        _full_history_running.add(race_id)
    def worker():
        ttl=max(1800,int(os.getenv("RACEDB_FULL_HISTORY_TTL_SEC","21600")));cutoff=str(detail.get("date") or _today_iso());circuit=str(detail.get("circuit") or "")
        try:
            if circuit=="地方":
                store=NarStore()
                try:
                    for h in horses:
                        key="fullhist:nar:"+RACEDB._horse_key(h);last=RACEDB.source_updated(key)
                        if last and int(time.time())-last<ttl:continue
                        try:
                            runs=store.recent_races(str(h.get("name") or ""),cutoff,100000)
                            n=RACEDB.upsert_past_runs(h,runs);RACEDB.mark_source(key,"done",f"{n} runs")
                        except Exception as exc:RACEDB.mark_source(key,"error",str(exc))
                finally:
                    try:store.conn.close()
                    except Exception:pass
            else:
                def one(h):
                    key="fullhist:jra:"+RACEDB._horse_key(h);last=RACEDB.source_updated(key)
                    if last and int(time.time())-last<ttl:return
                    cname=str(h.get("_jraHorseCname") or "")
                    if not cname:
                        RACEDB.mark_source(key,"unavailable","JRA horse id unavailable");return
                    try:
                        runs=_jra_profile_runs(cname,cutoff,10000)
                        n=RACEDB.upsert_past_runs(h,runs);RACEDB.mark_source(key,"done",f"{n} runs")
                    except Exception as exc:RACEDB.mark_source(key,"error",str(exc))
                workers=max(1,min(4,int(os.getenv("RACEDB_FULL_HISTORY_WORKERS","3"))))
                with ThreadPoolExecutor(max_workers=min(workers,max(1,len(horses)))) as pool:list(pool.map(one,horses))
            latest,_=PREPARED_STORE.get(race_id)
            if latest:
                latest=_precompute_detail_metrics(_attach_evaluation_context(_attach_stored_career(latest)))
                latest.setdefault("historySearch",{})["status"]="complete-local-history"
                pm=latest.setdefault("preparedMeta",{})
                pm.pop("diagnosisVersion",None)
                pm["diagnosisReady"]=False
                PREPARED_STORE.put(latest,force=True)
                RACEDB.upsert_race(latest)
        finally:
            with _full_history_lock:_full_history_running.discard(race_id)
    threading.Thread(target=worker,daemon=True).start()
