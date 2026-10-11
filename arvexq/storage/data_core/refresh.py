"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _data_core_snapshot(race_id: str, *, _fast_local_race_detail, _prepared_get_fresh, _racedb_get_fast) -> dict | None:
    return _prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)

def _data_core_refresh_race(race_id: str, force: bool=False, *, ARVEXQ_DATA_CORE_VERSION, PREPARED_STORE, RACEDB, _build_fast_diagnosis_snapshot, _data_core_health, _data_core_lock, _data_core_record_run, _data_core_result_due, _data_core_running, _data_core_snapshot, _data_core_store_health, _hydrate_fast_card_now, _refresh_result_fast, _schedule_track_environment, _start_central_history_search, _start_race_history_search, _today_iso, central_race_detail, hashlib, odds_refresh, payout_refresh, time) -> dict:
    rid = str(race_id or '')
    if not rid:
        return {'raceId': rid, 'ok': False, 'error': 'empty race id'}
    with _data_core_lock:
        if rid in _data_core_running:
            d = _data_core_snapshot(rid)
            return {'raceId': rid, 'ok': True, 'running': True, 'health': _data_core_health(d)}
        _data_core_running.add(rid)
    started = int(time.time())
    run_id = f'dc-{started}-{hashlib.sha1(rid.encode()).hexdigest()[:8]}'
    attempted = set()
    errors = []
    try:
        d = _data_core_snapshot(rid)
        before = _data_core_health(d)
        if force or before.get('card', {}).get('status') != 'ready':
            attempted.add('card')
            try:
                _hydrate_fast_card_now(rid, deep_history=False)
            except Exception as exc:
                errors.append('card:' + str(exc))
            d = _data_core_snapshot(rid)
        h = _data_core_health(d)
        if str((d or {}).get('date') or '') == _today_iso() and (force or h.get('odds', {}).get('status') != 'ready' or h.get('body_weight', {}).get('status') != 'ready'):
            attempted.update({'odds', 'body_weight'})
            try:
                odds_refresh(rid, 1)
            except Exception as exc:
                errors.append('live:' + str(exc))
            d = _data_core_snapshot(rid)
        h = _data_core_health(d)
        if force or h.get('environment', {}).get('status') != 'ready':
            attempted.add('environment')
            try:
                if rid.startswith('jra-'):
                    fresh = central_race_detail(rid)
                    if fresh:
                        base = d or fresh
                        for k in ('weather', 'condition', 'title', 'distance', 'surface', 'startTime', 'scheduledStartTime'):
                            if fresh.get(k) not in (None, '', 0, '不明'):
                                base[k] = fresh.get(k)
                        RACEDB.upsert_race(base)
                        PREPARED_STORE.put(base, force=True)
                        d = base
                else:
                    _schedule_track_environment(str((d or {}).get('date') or _today_iso()), str((d or {}).get('circuit') or '地方'), str((d or {}).get('track') or ''), True)
            except Exception as exc:
                errors.append('env:' + str(exc))
        h = _data_core_health(d)
        if force or h.get('history', {}).get('status') != 'ready':
            attempted.add('history')
            try:
                if rid.startswith('jra-'):
                    _start_central_history_search(rid, str((d or {}).get('date') or _today_iso()), force=bool(force))
                else:
                    names = [str(x.get('name') or '') for x in (d or {}).get('horses') or [] if x.get('name')]
                    if names:
                        _start_race_history_search(rid, str((d or {}).get('date') or _today_iso()), names, force=bool(force))
            except Exception as exc:
                errors.append('history:' + str(exc))
        h = _data_core_health(d)
        if _data_core_result_due(d or {}) and (force or h.get('result', {}).get('status') != 'ready'):
            attempted.add('result')
            try:
                _refresh_result_fast(rid)
            except Exception as exc:
                errors.append('result:' + str(exc))
            d = _data_core_snapshot(rid)
        h = _data_core_health(d)
        if h.get('result', {}).get('status') == 'ready' and (force or h.get('payouts', {}).get('status') != 'ready'):
            attempted.add('payouts')
            try:
                payout_refresh(rid)
            except Exception as exc:
                errors.append('payouts:' + str(exc))
            d = _data_core_snapshot(rid)
        h = _data_core_health(d)
        if force or h.get('analysis', {}).get('status') != 'ready':
            attempted.add('analysis')
            try:
                _build_fast_diagnosis_snapshot(rid, allow_network=False, deep_context=False)
            except Exception as exc:
                errors.append('analysis:' + str(exc))
            d = _data_core_snapshot(rid)
        after = _data_core_store_health(d, attempted, 'ARVEXQ Data Core')
        if isinstance(d, dict) and d.get('id'):
            d['dataCoreHealth'] = after
            d['dataCoreVersion'] = ARVEXQ_DATA_CORE_VERSION
            d['dataCoreUpdatedAt'] = int(time.time())
            try:
                RACEDB.upsert_race(d)
                PREPARED_STORE.put(d, force=True)
            except Exception as exc:
                errors.append('persist-health:' + str(exc))
        _data_core_record_run(run_id, rid, started, 'partial' if errors else 'ok', attempted, before, after, ' | '.join(errors[-5:]))
        return {'raceId': rid, 'ok': not errors, 'attempted': sorted(attempted), 'health': after, 'errors': errors[-5:], 'version': ARVEXQ_DATA_CORE_VERSION}
    finally:
        with _data_core_lock:
            _data_core_running.discard(rid)

def _data_core_day_rows(date: str, *, _bootstrap_rows_local) -> list[dict]:
    try:
        return _bootstrap_rows_local(date)
    except Exception:
        return []

def _data_core_day_status(date: str, circuit: str='', *, ARVEXQ_DATA_CORE_VERSION, DATA_CORE_FIELDS, RACEDB, _data_core_day_rows, _data_core_health, _data_core_snapshot, sqlite3) -> dict:
    rows = [r for r in _data_core_day_rows(date) if not circuit or str(r.get('circuit') or '') == str(circuit)]
    ids = [str(r.get('id') or '') for r in rows if r.get('id')]
    by = {rid: {} for rid in ids}
    if ids:
        conn = sqlite3.connect(RACEDB.path, timeout=3)
        conn.row_factory = sqlite3.Row
        try:
            marks = ','.join(('?' for _ in ids))
            for r in conn.execute(f'SELECT * FROM field_state WHERE race_id IN ({marks})', ids).fetchall():
                by.setdefault(str(r['race_id']), {})[str(r['field_key'])] = dict(r)
        finally:
            conn.close()
    fields = {k: {'ready': 0, 'partial': 0, 'missing': 0, 'pending': 0, 'not_due': 0} for k in DATA_CORE_FIELDS}
    ready_races = 0
    race_rows = []
    for r in rows:
        rid = str(r.get('id') or '')
        st = by.get(rid) or {}
        if not st:
            h = _data_core_health(_data_core_snapshot(rid))
            st = {k: {'status': v.get('status'), 'completeness': v.get('completeness'), 'source': v.get('source'), 'note': v.get('note')} for k, v in h.items()}
        for k in DATA_CORE_FIELDS:
            status = str((st.get(k) or {}).get('status') or 'missing')
            fields[k][status if status in fields[k] else 'missing'] += 1
        essential = ('card', 'history', 'odds', 'body_weight', 'environment', 'analysis')
        ready = all((str((st.get(k) or {}).get('status') or '') in ({'ready', 'not_due'} if k in {'odds', 'body_weight'} else {'ready'}) for k in essential))
        if ready:
            ready_races += 1
        race_rows.append({'id': rid, 'track': r.get('track'), 'raceNumber': r.get('raceNumber'), 'startTime': r.get('startTime'), 'ready': ready, 'fields': st})
    return {'version': ARVEXQ_DATA_CORE_VERSION, 'date': date, 'circuit': circuit, 'raceCount': len(rows), 'readyRaceCount': ready_races, 'fields': fields, 'races': race_rows}
