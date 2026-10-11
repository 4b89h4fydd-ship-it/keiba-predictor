"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _patch_nar_environment(date: str, track: str, rows: list[dict], env: dict, *, DB_PATH, _new_conn, _upcoming_rows) -> list[str]:
    if not env:
        return []
    affected = []
    upcoming = _upcoming_rows(rows)
    if not upcoming:
        return affected
    conn = _new_conn(DB_PATH)
    try:
        with conn:
            for r in upcoming:
                no = int(r.get('raceNumber') or 0)
                if not no:
                    continue
                sets = []
                args = []
                if env.get('weather') not in (None, '', '不明'):
                    sets.append('weather=?')
                    args.append(env['weather'])
                if env.get('condition') not in (None, '', '不明'):
                    sets.append('condition=?')
                    args.append(env['condition'])
                if sets:
                    args.extend([track, date, no])
                    conn.execute('UPDATE races SET ' + ','.join(sets) + ' WHERE track=? AND date=? AND race_no=?', args)
                    affected.append(str(r.get('id') or f'nar-{date}-{track}-{no:02d}'))
                scratch_map = env.get('scratchMap') or {}
                if scratch_map and int(env.get('raceNo') or 0) == no:
                    for horse_no, status in scratch_map.items():
                        conn.execute('UPDATE entries SET status=? WHERE track=? AND date=? AND race_no=? AND horse_no=?', (str(status), track, date, no, int(horse_no)))
                    rid = str(r.get('id') or f'nar-{date}-{track}-{no:02d}')
                    if rid not in affected:
                        affected.append(rid)
    finally:
        conn.close()
    return affected

def _patch_central_environment(rows: list[dict], env_by_surface: dict, weather: str, *, CentralStore, _upcoming_rows, time) -> list[str]:
    if not rows:
        return []
    upcoming = _upcoming_rows(rows)
    st = CentralStore()
    affected = []
    try:
        for r in upcoming:
            z = dict(r)
            changed = False
            if weather not in (None, '', '不明') and z.get('weather') != weather:
                z['weather'] = weather
                changed = True
            surf = str(z.get('surface') or '')
            cond = env_by_surface.get(surf) or (env_by_surface.get('芝') if surf == '障害' else None)
            if cond not in (None, '', '不明') and z.get('condition') != cond:
                z['condition'] = cond
                changed = True
            if changed:
                z['environmentMeta'] = {'source': 'JRA公式優先', 'updatedAtEpoch': int(time.time())}
                st.upsert([z])
                affected.append(str(z.get('id') or ''))
    finally:
        st.conn.close()
    return [x for x in affected if x]

def _refresh_track_environment(date: str, circuit: str, track: str, force: bool=False, *, _build_fast_diagnosis_snapshot, _environment_lock, _environment_state, _jra_fetch_environment, _nar_fetch_environment, _patch_central_environment, _patch_nar_environment, _race_list_cache, _race_list_cache_lock, _upcoming_rows, central_race_summaries, nar_race_summaries, time) -> dict:
    key = f'{date}|{circuit}|{track}'
    with _environment_lock:
        state = _environment_state.get(key) or {}
        if state.get('running'):
            return dict(state)
        if not force and int(time.time()) - int(state.get('updatedAtEpoch') or 0) < 25:
            return dict(state)
        _environment_state[key] = {'running': True, 'updatedAtEpoch': int(state.get('updatedAtEpoch') or 0), 'changed': 0, 'error': ''}
    affected = []
    error = ''
    try:
        rows = nar_race_summaries(date) if circuit == '地方' else central_race_summaries(date, allow_network=False)
        rows = [r for r in rows if str(r.get('track') or '') == str(track)]
        if not rows:
            return {'running': False, 'changed': 0}
        if circuit == '地方':
            reps = _upcoming_rows(rows)
            rep = reps[0] if reps else rows[0]
            env = _nar_fetch_environment(track, date, int(rep.get('raceNumber') or 0))
            if env:
                affected = _patch_nar_environment(date, track, rows, env)
        else:
            reps = _upcoming_rows(rows)
            by_surface = {}
            weather = '不明'
            for surf in ('芝', 'ダート', '障害'):
                cand = next((r for r in reps if str(r.get('surface') or '') == surf), None)
                if not cand:
                    continue
                env = _jra_fetch_environment(cand)
                if env.get('weather') not in (None, '', '不明'):
                    weather = env['weather']
                if env.get('condition') not in (None, '', '不明'):
                    by_surface[surf] = env['condition']
                for k, v in (env.get('surfaceConditions') or {}).items():
                    if v not in (None, '', '不明'):
                        by_surface[k] = v
            affected = _patch_central_environment(rows, by_surface, weather)
        if affected:
            with _race_list_cache_lock:
                [_race_list_cache.pop(k, None) for k in list(_race_list_cache) if k.startswith(date + '|')]
            for rid in affected:
                try:
                    _build_fast_diagnosis_snapshot(rid, allow_network=False, deep_context=False)
                except Exception as exc:
                    print('environment diagnosis rebuild failed', rid, exc)
    except Exception as exc:
        error = str(exc)
        print('track environment refresh failed', date, circuit, track, exc)
    finally:
        with _environment_lock:
            _environment_state[key] = {'running': False, 'updatedAtEpoch': int(time.time()), 'changed': len(affected), 'error': error}
    return dict(_environment_state.get(key) or {})

def _schedule_track_environment(date: str, circuit: str, track: str, force: bool=False, *, _environment_lock, _environment_running, _environment_state, _refresh_track_environment, threading, time) -> None:
    key = f'{date}|{circuit}|{track}'
    with _environment_lock:
        if key in _environment_running:
            return
        state = _environment_state.get(key) or {}
        if not force and int(time.time()) - int(state.get('updatedAtEpoch') or 0) < 25:
            return
        _environment_running.add(key)

    def worker():
        try:
            _refresh_track_environment(date, circuit, track, force)
        finally:
            with _environment_lock:
                _environment_running.discard(key)
    threading.Thread(target=worker, daemon=True, name='env-' + track).start()

def _environment_cycle(*, _schedule_track_environment, _today_iso, central_race_summaries, nar_race_summaries):
    date = _today_iso()
    rows = []
    try:
        rows.extend(nar_race_summaries(date))
    except Exception:
        pass
    try:
        rows.extend(central_race_summaries(date, allow_network=False))
    except Exception:
        pass
    groups = []
    seen = set()
    for r in rows:
        key = (str(r.get('circuit') or ''), str(r.get('track') or ''))
        if not key[0] or not key[1] or key[1] == '帯広' or (key in seen):
            continue
        seen.add(key)
        groups.append(key)
    for circuit, track in groups:
        _schedule_track_environment(date, circuit, track, False)

def _environment_loop(*, _environment_cycle, os, time):
    time.sleep(float(os.getenv('ENVIRONMENT_START_DELAY_SEC', '0.8')))
    while True:
        try:
            _environment_cycle()
        except Exception as exc:
            print('environment cycle failed', exc)
        time.sleep(max(30, int(os.getenv('ENVIRONMENT_REFRESH_SEC', '45'))))

def _start_environment_collector(*, _environment_loop, os, threading):
    enabled = str(os.getenv('ARVEXQ_ENVIRONMENT_COLLECTOR', '1')).lower() in {'1', 'true', 'yes', 'on'}
    if enabled:
        threading.Thread(target=_environment_loop, daemon=True, name='arvexq-environment').start()
