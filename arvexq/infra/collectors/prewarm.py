"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _prewarm_sort_key(row: dict, date: str, *, _now_jst, _today_iso) -> tuple:
    t = str(row.get('startTime') or '')
    try:
        hh, mm = t.split(':', 1)
        m = int(hh) * 60 + int(mm[:2])
    except Exception:
        m = 9999
    if date == _today_iso():
        now = _now_jst().hour * 60 + _now_jst().minute
        return (0 if m >= now else 1, m if m >= now else m + 1440, str(row.get('track') or ''), int(row.get('raceNumber') or 0))
    return (0, m, str(row.get('track') or ''), int(row.get('raceNumber') or 0))

def _schedule_prewarm(rows: list[dict], date: str, circuit: str='', *, ThreadPoolExecutor, _fast_local_race_detail, _prepared_get_fresh, _prewarm_lock, _prewarm_running, _prewarm_sort_key, _prewarm_state, _racedb_get_fast, _schedule_fast_card_refresh, _store_fast_snapshot, as_completed, os, threading, time) -> None:
    ordered = [r for r in sorted(rows, key=lambda x: _prewarm_sort_key(x, date)) if r.get('id') and (not circuit or r.get('circuit') == circuit)]
    max_races = max(1, int(os.getenv('PREWARM_MAX_RACES', '36')))
    ordered = ordered[:max_races]
    if not ordered:
        return
    key = f"{date}|{circuit or 'all'}"
    with _prewarm_lock:
        if key in _prewarm_running:
            return
        _prewarm_running.add(key)
        _prewarm_state[key] = {'running': True, 'done': 0, 'total': len(ordered), 'last': int(time.time()), 'errors': 0}

    def worker():
        done = errs = 0
        workers = max(1, min(int(os.getenv('PREWARM_WORKERS', '2')), len(ordered)))
        deep = max(0, int(os.getenv('PREWARM_DEEP_RACES', '3')))

        def one(ix_row):
            ix, row = ix_row
            rid = str(row.get('id') or '')
            detail = _prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
            if detail:
                if not (_prepared_get_fresh(rid) or _racedb_get_fast(rid)):
                    _store_fast_snapshot(detail)
            else:
                _schedule_fast_card_refresh(rid)
            return (rid, detail)
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(one, x) for x in enumerate(ordered)]
                for fut in as_completed(futures):
                    try:
                        _, detail = fut.result()
                        if detail:
                            done += 1
                        else:
                            errs += 1
                    except Exception as exc:
                        errs += 1
                        print('prewarm failed', exc)
                    with _prewarm_lock:
                        _prewarm_state[key] = {'running': True, 'done': done, 'total': len(ordered), 'last': int(time.time()), 'errors': errs}
        finally:
            with _prewarm_lock:
                _prewarm_running.discard(key)
                _prewarm_state[key] = {'running': False, 'done': done, 'total': len(ordered), 'last': int(time.time()), 'errors': errs}
    threading.Thread(target=worker, daemon=True).start()

def _ensure_detail_background_jobs(race_id: str, detail: dict, *, _central_detail_coverage, _enrichment_status, _history_counts, _history_is_enough, _race_history_status, _snapshot_final, _start_central_history_search, _start_enrichment, _start_race_history_search, _today_iso, assess_career_readiness) -> None:
    if detail.get('date') != _today_iso() or _snapshot_final(detail):
        return
    try:
        es = _enrichment_status(race_id)
        if es.get('status') in {'idle', 'unavailable'}:
            _start_enrichment(race_id, detail)
    except Exception as exc:
        print('prepared enrichment schedule failed', race_id, exc)
    try:
        if race_id.startswith('nar-'):
            names = [str(h.get('name') or '') for h in detail.get('horses', []) if h.get('name')]
            cov = _history_counts(names, detail.get('date') or '9999-12-31')
            if _race_history_status(race_id) is None and (not _history_is_enough(cov, 0)):
                _start_race_history_search(race_id, detail.get('date') or _today_iso(), names)
        else:
            cov = _central_detail_coverage(detail)
            total = int(cov.get('totalHorses') or 0)
            resolved = int(cov.get('horsesResolved') or cov.get('horsesWith5Plus') or 0)
            if detail.get('analysisMode') != '新馬' and _race_history_status(race_id) is None and (not assess_career_readiness(detail).get('ready')):
                _start_central_history_search(race_id, detail.get('date') or _today_iso())
    except Exception as exc:
        print('prepared history schedule failed', race_id, exc)

def _schedule_detail_background_jobs(race_id: str, detail: dict, *, _ensure_detail_background_jobs, threading) -> None:
    threading.Thread(target=_ensure_detail_background_jobs, args=(race_id, detail), daemon=True).start()
