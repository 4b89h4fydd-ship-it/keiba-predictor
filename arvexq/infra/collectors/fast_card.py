"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _ensure_fast_card_workers(*, _fast_card_cv, _fast_card_worker, os, threading, _state):
    with _fast_card_cv:
        if _state._fast_card_workers_started:
            return
        _state._fast_card_workers_started = True
        workers = max(1, min(6, int(os.getenv('FAST_CARD_WORKERS', '4'))))
        for idx in range(workers):
            threading.Thread(target=_fast_card_worker, daemon=True, name=f'fast-card-worker-{idx + 1}').start()

def _queue_fast_card(race_id: str, priority: int=50, *, _ensure_fast_card_workers, _fast_card_cv, _fast_card_pending, _fast_card_queue, _fast_card_running, time):
    if not race_id:
        return
    _ensure_fast_card_workers()
    with _fast_card_cv:
        if race_id in _fast_card_pending or race_id in _fast_card_running:
            return
        _fast_card_pending.add(race_id)
        _fast_card_queue.append((int(priority), time.time(), race_id))
        _fast_card_queue.sort(key=lambda x: (x[0], x[1]))
        _fast_card_cv.notify()

def _fast_card_worker(*, _build_fast_diagnosis_snapshot, _fast_card_cv, _fast_card_pending, _fast_card_queue, _fast_card_running, _hydrate_fast_card_now):
    while True:
        with _fast_card_cv:
            while not _fast_card_queue:
                _fast_card_cv.wait()
            priority, _, race_id = _fast_card_queue.pop(0)
            _fast_card_pending.discard(race_id)
            _fast_card_running.add(race_id)
        try:
            deep = priority <= 10
            _hydrate_fast_card_now(race_id, deep_history=deep)
            try:
                _build_fast_diagnosis_snapshot(race_id, allow_network=False, deep_context=deep)
            except Exception as exc:
                print('fast diagnosis after card failed', race_id, exc)
        except Exception as exc:
            print('fast card worker failed', race_id, exc)
        finally:
            with _fast_card_cv:
                _fast_card_running.discard(race_id)

def _schedule_fast_card_refresh(race_id: str, priority: int=50, *, _queue_fast_card) -> None:
    _queue_fast_card(race_id, priority)

def _schedule_racedb_snapshot_refresh(race_id: str, *, _ensure_detail_background_jobs, _prepare_race_snapshot, _racedb_refresh_lock, _racedb_refresh_running, threading) -> None:
    with _racedb_refresh_lock:
        if race_id in _racedb_refresh_running:
            return
        _racedb_refresh_running.add(race_id)

    def worker():
        try:
            fresh = _prepare_race_snapshot(race_id, True)
            if fresh:
                _ensure_detail_background_jobs(race_id, fresh)
        except Exception as exc:
            print('RaceDB refresh failed', race_id, exc)
        finally:
            with _racedb_refresh_lock:
                _racedb_refresh_running.discard(race_id)
    threading.Thread(target=worker, daemon=True).start()
