"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _data_core_cycle(*, ThreadPoolExecutor, _data_core_day_rows, _data_core_health, _data_core_lock, _data_core_refresh_race, _data_core_result_due, _data_core_snapshot, _data_core_state, _data_core_store_health, _now_jst, _race_minutes_server, _today_iso, os, time):
    with _data_core_lock:
        if _data_core_state.get('running'):
            return
        _data_core_state.update({'running': True, 'lastStart': int(time.time()), 'checked': 0, 'refreshed': 0, 'error': ''})
    checked = refreshed = 0
    errors = []
    try:
        rows = _data_core_day_rows(_today_iso())
        nowj = _now_jst()
        nowm = nowj.hour * 60 + nowj.minute
        candidates = []
        for r in rows:
            rid = str(r.get('id') or '')
            if not rid:
                continue
            d = _data_core_snapshot(rid)
            h = _data_core_health(d)
            checked += 1
            _data_core_store_health(d, set(), 'local') if d else None
            needed = [k for k in ('card', 'history', 'odds', 'body_weight', 'environment', 'analysis') if h.get(k, {}).get('status') not in {'ready', 'not_due'}]
            if _data_core_result_due(d or r) and h.get('result', {}).get('status') != 'ready':
                needed.append('result')
            if h.get('result', {}).get('status') == 'ready' and h.get('payouts', {}).get('status') != 'ready':
                needed.append('payouts')
            if needed:
                st = _race_minutes_server(r)
                dist = abs(st - nowm) if st < 9999 else 9999
                candidates.append((dist, st, rid, needed))
        candidates.sort(key=lambda x: (x[0], x[1]))
        targets = candidates[:max(1, int(os.getenv('ARVEXQ_DATA_CORE_BATCH', '16')))]
        workers = max(1, min(8, len(targets))) if targets else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for z in pool.map(lambda x: _data_core_refresh_race(x[2], False), targets):
                    refreshed += 1
                    if not z.get('ok') and z.get('errors'):
                        errors.extend(z.get('errors') or [])
    except Exception as exc:
        errors.append(str(exc))
    finally:
        with _data_core_lock:
            _data_core_state.update({'running': False, 'lastFinish': int(time.time()), 'checked': checked, 'refreshed': refreshed, 'error': ' | '.join(errors[-5:])})

def _data_core_loop(*, _data_core_cycle, os, time):
    time.sleep(float(os.getenv('ARVEXQ_DATA_CORE_START_DELAY_SEC', '1.2')))
    while True:
        try:
            _data_core_cycle()
        except Exception as exc:
            print('ARVEXQ Data Core cycle failed', exc)
        time.sleep(max(10, int(os.getenv('ARVEXQ_DATA_CORE_LOOP_SEC', '12'))))

def _start_data_core_collector(*, _data_core_loop, os, threading):
    enabled = str(os.getenv('ARVEXQ_DATA_CORE', '1')).lower() in {'1', 'true', 'yes', 'on'}
    if enabled:
        threading.Thread(target=_data_core_loop, daemon=True, name='arvexq-data-core').start()
