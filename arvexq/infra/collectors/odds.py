"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _auto_odds_targets(*, _now_jst, _race_minutes_server, _snapshot_final, _today_iso, central_race_summaries, nar_race_summaries) -> list[dict]:
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
    nowj = _now_jst()
    nowm = nowj.hour * 60 + nowj.minute
    out = []
    for r in rows:
        if not r.get('id') or _snapshot_final(r):
            continue
        start = _race_minutes_server(r)
        if start >= 9999:
            out.append(r)
            continue
        remain = start - nowm
        if remain < -8:
            continue
        out.append(r)
    out.sort(key=lambda r: _race_minutes_server(r))
    return out

def _auto_odds_cycle(*, ThreadPoolExecutor, _auto_odds_last, _auto_odds_lock, _auto_odds_state, _auto_odds_targets, _now_jst, _race_minutes_server, odds_refresh, os, time):
    with _auto_odds_lock:
        if _auto_odds_state.get('running'):
            return
        _auto_odds_state.update({'running': True, 'lastStart': int(time.time()), 'checked': 0, 'updated': 0, 'error': ''})
    checked = updated = 0
    errors = []
    try:
        now = time.time()
        targets = []
        nowj = _now_jst()
        nowm = nowj.hour * 60 + nowj.minute
        for r in _auto_odds_targets():
            rid = str(r.get('id') or '')
            start = _race_minutes_server(r)
            remain = start - nowm if start < 9999 else 9999
            cadence = 30 if remain <= 30 else 60 if remain <= 180 else 180
            last = float(_auto_odds_last.get(rid, 0))
            if now - last < cadence:
                continue
            _auto_odds_last[rid] = now
            targets.append(r)

        def one(r):
            rid = str(r.get('id') or '')
            try:
                last_body = None
                for attempt in range(2):
                    last_body = odds_refresh(rid, 1)
                    hs = (last_body or {}).get('horses') or []
                    live = [h for h in hs if not h.get('scratched') and int(h.get('horseNumber') or 0) > 0]
                    got = sum((1 for h in live if float(h.get('winOdds') or 0) > 0))
                    weights = sum((1 for h in live if int(h.get('bodyWeight') or 0) > 250))
                    if live and got == len(live):
                        return (rid, {'complete': True, 'odds': got, 'field': len(live), 'weights': weights})
                    if attempt == 0:
                        time.sleep(0.15)
                return (rid, {'complete': False, 'odds': got if 'got' in locals() else 0, 'field': len(live) if 'live' in locals() else 0, 'weights': weights if 'weights' in locals() else 0})
            except Exception as exc:
                return (rid, exc)
        workers = max(1, min(20, int(os.getenv('AUTO_ODDS_WORKERS', '18')), len(targets))) if targets else 0
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for rid, res in pool.map(one, targets):
                    checked += 1
                    if isinstance(res, dict) and res.get('complete'):
                        updated += 1
                    elif isinstance(res, dict):
                        _auto_odds_last[rid] = min(float(_auto_odds_last.get(rid, 0)), time.time() - 20)
                    elif isinstance(res, Exception):
                        errors.append(rid + ': ' + str(res))
    finally:
        with _auto_odds_lock:
            _auto_odds_state.update({'running': False, 'lastFinish': int(time.time()), 'checked': checked, 'updated': updated, 'error': ' | '.join(errors[-5:])})

def _auto_odds_loop(*, _auto_odds_cycle, os, time):
    time.sleep(float(os.getenv('AUTO_ODDS_START_DELAY_SEC', '0.7')))
    while True:
        try:
            _auto_odds_cycle()
        except Exception as exc:
            print('auto odds cycle failed', exc)
        time.sleep(max(8, int(os.getenv('AUTO_ODDS_LOOP_SEC', '10'))))

def _start_auto_odds_collector(*, _auto_odds_loop, os, threading):
    enabled = str(os.getenv('ARVEXQ_AUTO_ODDS', '1')).lower() in {'1', 'true', 'yes', 'on'}
    if enabled:
        threading.Thread(target=_auto_odds_loop, daemon=True, name='arvexq-auto-odds').start()
