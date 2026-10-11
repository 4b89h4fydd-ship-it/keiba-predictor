"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _history_worker(months_back: int | None=None, *, _sync_nar_month_wave, datetime, iter_months_back, os, time, _state):
    time.sleep(float(os.getenv('HISTORY_START_DELAY_SEC', '0.15')))
    today = datetime.now().date()
    if months_back is None:
        months_back = max(2, min(8, int(os.getenv('NAR_HISTORY_WARM_MONTHS', '4'))))
    seen = set()
    jobs = []
    for y, m in [(today.year, today.month)] + list(iter_months_back(today, months_back - 1)):
        if (y, m) not in seen:
            jobs.append((y, m))
            seen.add((y, m))
    try:
        _, errors = _sync_nar_month_wave(jobs)
        _state._history_error = ' | '.join(errors)
    except Exception as exc:
        _state._history_error = str(exc)
    _state._history_ready = True

def ensure_history_async(*, _history_lock, _history_worker, threading, _state):
    with _history_lock:
        if _state._history_started:
            return
        _state._history_started = True
        threading.Thread(target=_history_worker, daemon=True).start()
