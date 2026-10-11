"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _assemble_day_bundle(date: str, allow_network_fill: bool=False, *, ThreadPoolExecutor, _bootstrap_analysis_ready, _bootstrap_detail_local, _bootstrap_display_ready, _bootstrap_rows_local, _bootstrap_sources_running, as_completed, os, time) -> dict:
    rows = _bootstrap_rows_local(date)
    details = []
    if rows:
        workers = max(1, min(8, int(os.getenv('DAY_BUNDLE_WORKERS', '6')), len(rows)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_bootstrap_detail_local, str(r.get('id')), allow_network_fill): str(r.get('id')) for r in rows}
            for fut in as_completed(futures):
                try:
                    d = fut.result()
                except Exception as exc:
                    print('day bundle race failed', futures[fut], exc)
                    d = None
                if d and d.get('id'):
                    details.append(d)
    details.sort(key=lambda d: (str(d.get('circuit') or ''), str(d.get('track') or ''), int(d.get('raceNumber') or 0)))
    display_ids = {str(d.get('id') or '') for d in details if _bootstrap_display_ready(d)}
    analysis_ids = {str(d.get('id') or '') for d in details if _bootstrap_analysis_ready(d)}
    missing = [str(r.get('id') or '') for r in rows if str(r.get('id') or '') not in display_ids]
    source_running = _bootstrap_sources_running(date)
    display_complete = bool(rows) and (not missing) and (not source_running)
    return {'date': date, 'races': rows, 'details': details, 'raceCount': len(rows), 'detailCount': len(display_ids), 'analysisCount': len(analysis_ids), 'missing': missing, 'complete': display_complete, 'displayComplete': display_complete, 'analysisComplete': bool(rows) and len(analysis_ids) >= len(rows), 'sourceRunning': source_running, 'generatedAtEpoch': int(time.time()), 'source': 'nonblocking-day-bundle'}

def _refresh_day_bundle(date: str, force_sources: bool=False, wait_for_complete: bool=False, timeout_sec: float=25.0, *, DAY_BUNDLES, _assemble_day_bundle, _bootstrap_analysis_ready, _schedule_central_refresh, _schedule_fast_card_refresh, _schedule_live_refresh, _site_bootstrap_build_lock, _site_bootstrap_cache, _site_bootstrap_lock, _site_bootstrap_state, _today_iso, time) -> dict:
    """Single-pass bundle refresh. Missing/outdated races are queued and never block the caller."""
    started = time.time()
    with _site_bootstrap_build_lock:
        with _site_bootstrap_lock:
            _site_bootstrap_state[date] = {'running': True, 'startedAt': int(started), 'raceCount': 0, 'ready': 0, 'missing': []}
        if force_sources or date == _today_iso():
            try:
                _schedule_live_refresh(date, force=bool(force_sources))
            except Exception:
                pass
            try:
                _schedule_central_refresh(date, force=bool(force_sources))
            except Exception:
                pass
        payload = _assemble_day_bundle(date, allow_network_fill=False)
        missing = list(payload.get('missing') or [])
        for rid in missing:
            _schedule_fast_card_refresh(rid, 5)
        for d in payload.get('details') or []:
            if d and d.get('id') and (not _bootstrap_analysis_ready(d)):
                _schedule_fast_card_refresh(str(d.get('id')), 12)
        try:
            DAY_BUNDLES.put(date, payload, bool(payload.get('displayComplete')))
        except Exception:
            pass
        with _site_bootstrap_lock:
            _site_bootstrap_cache[date] = (time.time(), payload)
            _site_bootstrap_state[date] = {'running': False, 'startedAt': int(started), 'finishedAt': int(time.time()), 'raceCount': int(payload.get('raceCount') or 0), 'ready': int(payload.get('detailCount') or 0), 'analysisReady': int(payload.get('analysisCount') or 0), 'missing': missing, 'sourceRunning': bool(payload.get('sourceRunning')), 'elapsedMs': int((time.time() - started) * 1000)}
        return payload

def _schedule_day_bundle_refresh(date: str, force_sources: bool=False, *, _refresh_day_bundle, _site_bootstrap_lock, _site_bootstrap_state, os, threading, time) -> None:
    with _site_bootstrap_lock:
        st = _site_bootstrap_state.get(date) or {}
        if st.get('running'):
            return
        _site_bootstrap_state[date] = {'running': True, 'startedAt': int(time.time()), 'raceCount': 0, 'ready': 0, 'missing': []}

    def worker():
        try:
            _refresh_day_bundle(date, force_sources, True, float(os.getenv('DAY_BUNDLE_BUILD_TIMEOUT_SEC', '45')))
        except Exception as exc:
            print('day bundle refresh failed', date, exc)
            with _site_bootstrap_lock:
                st = dict(_site_bootstrap_state.get(date) or {})
                st.update({'running': False, 'error': str(exc), 'finishedAt': int(time.time())})
                _site_bootstrap_state[date] = st
    threading.Thread(target=worker, daemon=True, name='day-bundle-' + date).start()
