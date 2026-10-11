"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _site_bootstrap_payload(date: str, force: bool=False, wait: bool=False, *, DAY_BUNDLES, _assemble_day_bundle, _bundle_quality, _schedule_day_bundle_refresh, _site_bootstrap_lock, _site_force_cache, _today_iso, time) -> dict:
    """
    Customer path is strictly non-blocking.
    Return the best local bundle immediately, then continue full preparation in background.
    v240: a fresh force=1 collector result must not be immediately replaced by an
    older persisted bundle on the next non-force poll.
    """
    stored = DAY_BUNDLES.get(date, complete_only=True)
    recent_force = None
    with _site_bootstrap_lock:
        fc = _site_force_cache.get(date)
        if fc and time.time() - float(fc[0]) <= 60:
            recent_force = dict(fc[1])
    if not force and recent_force and (not stored or _bundle_quality(recent_force) >= _bundle_quality(stored)):
        out = dict(recent_force)
        out['cached'] = False
        out['servedFrom'] = 'recent-force-live'
        return out
    if stored and (not force):
        if date == _today_iso() and int(time.time()) - int(stored.get('updatedAtEpoch') or 0) > 20:
            _schedule_day_bundle_refresh(date, False)
        out = dict(stored)
        out['cached'] = True
        out['servedFrom'] = 'persistent-display-complete'
        return out
    try:
        current = _assemble_day_bundle(date, allow_network_fill=False)
    except Exception as exc:
        print('nonblocking bootstrap assemble failed', date, exc)
        current = {'date': date, 'races': [], 'details': [], 'raceCount': 0, 'detailCount': 0, 'analysisCount': 0, 'missing': [], 'complete': False, 'displayComplete': False, 'analysisComplete': False, 'sourceRunning': False, 'generatedAtEpoch': int(time.time()), 'source': 'nonblocking-day-bundle'}
    if current.get('displayComplete'):
        try:
            DAY_BUNDLES.put(date, current, True)
        except Exception:
            pass
    _schedule_day_bundle_refresh(date, bool(force))
    current['cached'] = False
    current['servedFrom'] = 'local-immediate'
    return current
