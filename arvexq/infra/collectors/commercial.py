"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _commercial_collect_once(*, PREDICTION_ENGINE_VERSION, _commercial_collector_lock, _commercial_collector_state, _commercial_target_rows, _fast_local_race_detail, _now_jst, _prepared_get_fresh, _race_list_cache, _race_list_cache_lock, _racedb_get_fast, _schedule_central_refresh, _schedule_day_bundle_refresh, _schedule_fast_card_refresh, _schedule_live_refresh, _today_iso, central_race_summaries, nar_race_summaries, os, time):
    started = time.time()
    with _commercial_collector_lock:
        if _commercial_collector_state['running']:
            return
        _commercial_collector_state.update({'running': True, 'lastStart': started, 'lastError': '', 'hydrated': 0, 'diagnosed': 0})
    queued = ready = 0
    errs = []
    try:
        today = _today_iso()
        _schedule_live_refresh(today, False)
        _schedule_central_refresh(today, False)
        time.sleep(float(os.getenv('COMMERCIAL_LIST_SETTLE_SEC', '1.2')))
        rows = []
        try:
            rows.extend(nar_race_summaries(today))
        except Exception as exc:
            errs.append('NAR list: ' + str(exc))
        try:
            rows.extend(central_race_summaries(today, allow_network=False))
        except Exception as exc:
            errs.append('JRA list: ' + str(exc))
        nowj = _now_jst()
        now_min = nowj.hour * 60 + nowj.minute
        targets = _commercial_target_rows(rows, now_min)
        for idx, r in enumerate(targets):
            rid = str(r.get('id') or '')
            if not rid:
                continue
            d = _prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
            pm = (d or {}).get('preparedMeta') or {}
            if d and pm.get('diagnosisVersion') == PREDICTION_ENGINE_VERSION and pm.get('diagnosisReady'):
                ready += 1
                continue
            priority = 20 + idx
            _schedule_fast_card_refresh(rid, priority)
            queued += 1
        with _race_list_cache_lock:
            _race_list_cache.clear()
        _schedule_day_bundle_refresh(today, False)
    except Exception as exc:
        errs.append(str(exc))
    finally:
        finished = time.time()
        with _commercial_collector_lock:
            _commercial_collector_state.update({'running': False, 'lastFinish': finished, 'lastError': ' | '.join(errs[-6:]), 'hydrated': ready, 'diagnosed': ready, 'queued': queued, 'cycleSec': round(finished - started, 2)})

def _commercial_collector_loop(*, _commercial_collect_once, os, time):
    first_delay = float(os.getenv('COMMERCIAL_COLLECTOR_START_DELAY_SEC', '1.0'))
    interval = max(120, int(os.getenv('COMMERCIAL_COLLECTOR_INTERVAL_SEC', '180')))
    time.sleep(first_delay)
    while True:
        try:
            _commercial_collect_once()
        except Exception as exc:
            print('commercial collector cycle failed', exc)
        time.sleep(interval)

def _start_commercial_collector(*, _commercial_collector_loop, os, threading):
    enabled = str(os.getenv('ARVEXQ_COMMERCIAL_COLLECTOR', '1')).lower() in {'1', 'true', 'yes', 'on'}
    if enabled:
        threading.Thread(target=_commercial_collector_loop, daemon=True, name='arvexq-commercial-collector').start()
