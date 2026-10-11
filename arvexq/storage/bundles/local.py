"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _bootstrap_rows_local(date: str, *, races) -> list[dict]:
    raw = races(date, '', 0, 0)
    rows = raw.get('races', []) if isinstance(raw, dict) else list(raw or [])
    out = []
    seen = set()
    for r in rows:
        rid = str(r.get('id') or '')
        if not rid or rid in seen:
            continue
        seen.add(rid)
        out.append(r)
    out.sort(key=lambda r: (str(r.get('circuit') or ''), str(r.get('track') or ''), int(r.get('raceNumber') or 0)))
    return out

def _bootstrap_sources_running(date: str, *, _central_refresh_status, _live_refresh_lock, _live_refresh_running) -> bool:
    running = False
    try:
        with _live_refresh_lock:
            running = running or f'live:{date}' in _live_refresh_running
    except Exception:
        pass
    try:
        running = running or bool(_central_refresh_status(date).get('running'))
    except Exception:
        pass
    return bool(running)

def _bootstrap_analysis_ready(d: dict | None, *, PREDICTION_ENGINE_VERSION, _bootstrap_display_ready, _snapshot_final) -> bool:
    """Diagnosis readiness is tracked separately and must never block site display."""
    if not _bootstrap_display_ready(d):
        return False
    if _snapshot_final(d):
        return True
    pm = d.get('preparedMeta') or {}
    return bool(pm.get('diagnosisReady') and pm.get('diagnosisVersion') == PREDICTION_ENGINE_VERSION)

def _bootstrap_detail_local(race_id: str, force_hydrate: bool=False, *, _bootstrap_analysis_ready, _compact_display_snapshot, _ensure_race_volatility, _fast_local_race_detail, _prepared_get_fresh, _racedb_get_fast, _restore_saved_odds, _schedule_fast_card_refresh) -> dict | None:
    """Fast local snapshot for day bundles. Heavy diagnosis work is background-only."""
    d = _prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if not d:
        try:
            d = _fast_local_race_detail(race_id)
        except Exception:
            d = None
    if not d:
        if force_hydrate:
            _schedule_fast_card_refresh(race_id, 5)
        return None
    d = _restore_saved_odds(d)
    d = _ensure_race_volatility(d)
    if force_hydrate and (not _bootstrap_analysis_ready(d)):
        _schedule_fast_card_refresh(race_id, 8)
    return _compact_display_snapshot(d)
