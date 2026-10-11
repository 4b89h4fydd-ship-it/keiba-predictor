"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _racedb_live_cycle(*, _now_jst, _schedule_central_refresh, _schedule_live_refresh, _schedule_prewarm, _today_iso, central_race_summaries, nar_race_summaries, odds_refresh, os, re) -> None:
    today = _today_iso()
    rows = []
    _schedule_live_refresh(today, False)
    _schedule_central_refresh(today, False)
    try:
        rows.extend(nar_race_summaries(today))
    except Exception as exc:
        print('RaceDB NAR list failed', exc)
    try:
        rows.extend(central_race_summaries(today, allow_network=True, force=False))
    except Exception as exc:
        print('RaceDB JRA list failed', exc)
    if rows:
        _schedule_prewarm(rows, today, '')
    if not bool(int(os.getenv('RACEDB_AUTO_ODDS', '1'))):
        return
    nowm = _now_jst().hour * 60 + _now_jst().minute
    window = int(os.getenv('RACEDB_ODDS_WINDOW_MIN', '90'))
    limit = max(1, int(os.getenv('RACEDB_ODDS_MAX_RACES', '4')))
    upcoming = []
    for r in rows:
        if r.get('result'):
            continue
        t = str(r.get('startTime') or '')
        m = re.match('^(\\d{1,2}):(\\d{2})', t)
        if not m:
            continue
        rm = int(m.group(1)) * 60 + int(m.group(2))
        delta = rm - nowm
        if -5 <= delta <= window:
            upcoming.append((delta, r))
    upcoming.sort(key=lambda x: x[0])
    for _, r in upcoming[:limit]:
        try:
            odds_refresh(str(r.get('id') or ''))
        except Exception as exc:
            print('RaceDB automatic odds failed', r.get('id'), exc)

def _start_racedb_daemon(*, _racedb_daemon_lock, _racedb_live_cycle, os, threading, time, _state) -> None:
    if str(os.getenv('ARVEXQ_COMMERCIAL_COLLECTOR', '1')).lower() in {'1', 'true', 'yes', 'on'}:
        return
    if not bool(int(os.getenv('RACEDB_AUTO_UPDATE', '1'))):
        return
    with _racedb_daemon_lock:
        if _state._racedb_daemon_started:
            return
        _state._racedb_daemon_started = True

    def worker():
        time.sleep(float(os.getenv('RACEDB_START_DELAY_SEC', '2')))
        while True:
            try:
                _racedb_live_cycle()
            except Exception as exc:
                print('RaceDB live cycle failed', exc)
            time.sleep(max(30, int(os.getenv('RACEDB_UPDATE_SEC', '120'))))
    threading.Thread(target=worker, daemon=True, name='RaceDB-live-updater').start()
