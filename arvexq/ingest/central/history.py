"""central/history: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.history.central_rows import _central_run_from_race
from arvexq.ingest.jra_career_merge import merge_full_profile_history
from arvexq.ingest.scheduling import _months_from_race_date
from arvexq.normalize.scalars import _clean
from arvexq.prediction.career_readiness import assess_career_readiness
from arvexq.prediction.pure_diagnostics import _central_detail_coverage
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from datetime import date as dt_date
from datetime import datetime
import calendar
import json
import os
import threading


from arvexq.ingest.history.jobs import _race_history_jobs
from arvexq.ingest.history.jobs import _race_history_lock

def _central_resolve_race_id(run: dict, *, CENTRAL_DB_PATH, _new_conn) -> str:
    if run.get("raceId"):
        return str(run.get("raceId"))
    d = _clean(str(run.get("date") or ""))
    tr = _clean(str(run.get("track") or ""))
    rn = int(run.get("raceNumber") or 0)
    if not d or not tr or rn <= 0 or not CENTRAL_DB_PATH.exists():
        return ""
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        row = conn.execute(
            "SELECT id FROM central_races WHERE date=? AND track=? AND race_no=? LIMIT 1",
            (d, tr, rn),
        ).fetchone()
        return str(row["id"]) if row else ""
    finally:
        conn.close()


def _central_recent_from_store(horse_name: str, cutoff: str, limit: int=5, *, CENTRAL_DB_PATH, _new_conn) -> list[dict]:
    if not CENTRAL_DB_PATH.exists() or not horse_name:
        return []
    conn = _new_conn(CENTRAL_DB_PATH)
    try:
        # Pull newest races first. We stop as soon as this horse has five actual starts.
        rows = conn.execute(
            "SELECT payload FROM central_races WHERE date<? ORDER BY date DESC,track DESC,race_no DESC LIMIT 4000",
            (cutoff,),
        ).fetchall()
        out = []
        seen = set()
        for row in rows:
            try:
                race = json.loads(row["payload"])
            except Exception:
                continue
            run = _central_run_from_race(race, horse_name)
            if not run:
                continue
            key = (run.get("date"), run.get("track"), int(run.get("raceNumber") or 0))
            if key in seen:
                continue
            seen.add(key)
            # A finish can be missing in a future-entry payload. Keep the race only when
            # the historical payload contains an actual result or explicit run result data.
            if int(run.get("finish") or 0) <= 0 and not run.get("cornerPositions") and not float(run.get("timeSeconds") or 0):
                continue
            out.append(run)
            if len(out) >= limit:
                break
        return out
    finally:
        conn.close()


def _merge_central_recent(existing: list[dict], stored: list[dict], cutoff: str, limit: int=5, *, _central_resolve_race_id) -> list[dict]:
    all_runs = []
    seen = set()
    for src in (existing or []) + (stored or []):
        if not isinstance(src, dict):
            continue
        run = dict(src)
        if cutoff and run.get("date") and str(run.get("date")) >= cutoff:
            continue
        rid = _central_resolve_race_id(run)
        if rid:
            run["raceId"] = rid
        key = run.get("raceId") or (str(run.get("date") or "") + "|" + str(run.get("track") or "") + "|" + str(int(run.get("raceNumber") or 0)))
        if key in seen:
            continue
        seen.add(key)
        all_runs.append(run)
    all_runs.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("raceNumber") or 0)), reverse=True)
    return all_runs[:limit]


def _central_month_dates(year: int, month: int, cutoff: str) -> list[str]:
    last = calendar.monthrange(year, month)[1]
    cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d").date()
    dates = []
    # JRA standard meetings are Sat/Sun and holiday Mondays. Searching these days first
    # avoids hundreds of empty requests while still covering ordinary and holiday meetings.
    for day in range(last, 0, -1):
        d = dt_date(year, month, day)
        if d >= cutoff_date:
            continue
        if d.weekday() in (0, 5, 6):
            dates.append(d.isoformat())
    return dates


def _fetch_central_days_parallel(days: list[str], *, fetch_central_feed) -> tuple[list[dict], list[str]]:
    if not days:
        return [], []
    workers = max(2, min(10, int(os.getenv("CENTRAL_HISTORY_WORKERS", "6"))))
    rows: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(days))) as pool:
        future_map = {pool.submit(fetch_central_feed, day, True):day for day in days}
        for fut in as_completed(future_map):
            day = future_map[fut]
            try:
                rows.extend(fut.result() or [])
            except Exception as exc:
                errors.append(f"{day}:{exc}")
    return rows, errors


def _start_central_history_search(race_id: str, iso_date: str, force: bool=False, *, CentralStore, _central_month_dates, _detail_cache, _detail_cache_lock, _fetch_central_days_parallel, _jra_profile_runs, central_race_detail) -> dict:
    max_months = max(12, min(60, int(os.getenv("CENTRAL_ON_DEMAND_HISTORY_MONTHS", "36"))))
    detail = central_race_detail(race_id)
    cov = _central_detail_coverage(detail or {})
    with _race_history_lock:
        existing = _race_history_jobs.get(race_id)
        if existing and not force:
            return dict(existing)
        has_feed=bool(_clean(os.getenv("CENTRAL_HISTORY_FEED_URL", "")) or _clean(os.getenv("CENTRAL_FEED_URL", "")))
        job = {"status":"running","monthsDone":0,"maxMonths":max_months,"coverage":cov,"error":"",
               "source":"中央フィード高速並列検索" if has_feed else "JRA公式 競走馬情報5走補完"}
        _race_history_jobs[race_id] = job

    def worker():
        errors = []
        months_done = 0
        store = CentralStore()
        try:
            # With no external central feed, use each horse's official JRA profile directly.
            if not has_feed:
                current=central_race_detail(race_id) or {}
                horses=current.get("horses") or []
                cutoff=current.get("date") or iso_date
                # The official profile page may contain far more than five
                # performances. Preserve its entire available pre-race career
                # in allPastRuns, keeping only recentRaces at five for the UI.
                history_limit=max(6,min(1000,int(os.getenv("ARVEXQ_CAREER_FETCH_LIMIT","1000"))))
                def fill(h):
                    h=dict(h)
                    try:
                        cname=h.get("_jraHorseCname") or h.get("jraHorseCname") or ""
                        extra=_jra_profile_runs(cname,cutoff,history_limit)
                        h=merge_full_profile_history(h,extra,cutoff)
                    except Exception as exc:
                        errors.append(str(exc))
                    return h
                workers=max(2,min(8,int(os.getenv("JRA_PROFILE_WORKERS","6"))))
                with ThreadPoolExecutor(max_workers=min(workers,max(1,len(horses)))) as pool:
                    current["horses"]=list(pool.map(fill,horses)) if horses else []
                current["source"]="JRA公式"
                store.upsert([current])
                fresh_detail=central_race_detail(race_id) or current
                cov_now=_central_detail_coverage(fresh_detail)
                total_now=int(cov_now.get("totalHorses") or 0)
                resolved_now=int(cov_now.get("horsesResolved") or cov_now.get("horsesWith5Plus") or 0)
                # A debut/young horse can legitimately have 0 prior runs. If JRA says the
                # inspected career is complete, treat it as resolved instead of a fetch error.
                central_done=bool(assess_career_readiness(fresh_detail).get("ready"))
                with _race_history_lock:
                    _race_history_jobs[race_id]={"status":"done" if central_done else ("error" if errors and not cov_now.get("horsesWithHistory",0) else "partial"),
                        "monthsDone":0,"maxMonths":0,"coverage":cov_now,"error":" | ".join(errors[-5:]),
                        "source":"JRA公式 競走馬情報全過去走補完","fullCareerVerified":central_done}
                with _detail_cache_lock:
                    _detail_cache.pop(race_id,None)
                return
            for y, m in _months_from_race_date(iso_date, max_months):
                days = _central_month_dates(y, m, iso_date)
                fresh_rows, errs = _fetch_central_days_parallel(days)
                errors.extend(errs)
                if fresh_rows:
                    store.upsert(fresh_rows)
                months_done += 1
                fresh_detail = central_race_detail(race_id) or {}
                cov_now = _central_detail_coverage(fresh_detail)
                with _race_history_lock:
                    _race_history_jobs[race_id] = {"status":"running","monthsDone":months_done,"maxMonths":max_months,
                                                   "coverage":cov_now,"error":" | ".join(errors[-3:]),"source":"中央フィード高速並列検索"}
                if assess_career_readiness(fresh_detail).get("ready"):
                    break
            fresh_detail = central_race_detail(race_id) or {}
            cov_now = _central_detail_coverage(fresh_detail)
            verified=bool(assess_career_readiness(fresh_detail).get("ready"))
            status = "done" if verified else ("error" if errors and not cov_now.get("horsesWithHistory",0) else "partial")
            with _race_history_lock:
                _race_history_jobs[race_id] = {"status":status,"monthsDone":months_done,"maxMonths":max_months,
                                               "coverage":cov_now,"error":" | ".join(errors[-5:]),"source":"中央フィード高速並列検索",
                                               "fullCareerVerified":verified}
            with _detail_cache_lock:
                _detail_cache.pop(race_id, None)
        finally:
            try:
                store.conn.close()
            except Exception:
                pass
    threading.Thread(target=worker, daemon=True).start()
    return dict(job)
