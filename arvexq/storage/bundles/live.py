"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _force_day_live_snapshot(date: str, timeout_sec: float=23.0, *, ARVEXQ_DATA_CORE_VERSION, DAY_BUNDLES, ThreadPoolExecutor, _assemble_day_bundle, _bootstrap_analysis_ready, _bootstrap_display_ready, _bootstrap_rows_local, _bootstrap_sources_running, _build_fast_diagnosis_snapshot, _compact_display_snapshot, _data_core_store_health, _fast_local_race_detail, _hydrate_fast_card_now, _now_jst, _prepared_get_fresh, _race_minutes_server, _racedb_get_fast, _refresh_result_fast, _schedule_central_refresh, _schedule_live_refresh, _site_bootstrap_cache, _site_bootstrap_lock, _site_bootstrap_payload, _site_force_cache, _snapshot_final, odds_refresh, os, time, wait) -> dict:
    """GitHub collector path: all-card live fields first, diagnosis second.

    v304 refreshed each race as one long job (card -> odds -> result -> diagnosis).
    Slow diagnosis jobs could occupy all workers and starve later races before their
    odds call ever started.  v305 splits the phases: every race gets an odds attempt
    first; only then do we spend the remaining budget on results/diagnosis.
    """
    started = time.time()
    try:
        _schedule_live_refresh(date, force=True)
    except Exception:
        pass
    try:
        _schedule_central_refresh(date, force=True)
    except Exception:
        pass
    deadline = started + max(8.0, float(timeout_sec))
    while time.time() < deadline and _bootstrap_sources_running(date):
        if time.time() - started > 2.2:
            break
        time.sleep(0.15)
    rows = _bootstrap_rows_local(date)
    if not rows:
        return _site_bootstrap_payload(date, True, False)

    def snapshot(rid: str) -> dict:
        return _prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid) or {}

    def live_coverage(d: dict) -> tuple[int, int, int]:
        hs = [h for h in d.get('horses') or [] if not h.get('scratched') and int(h.get('horseNumber') or 0) > 0]
        got = sum((1 for h in hs if float(h.get('winOdds') or 0) > 0))
        weights = sum((1 for h in hs if int(h.get('bodyWeight') or 0) > 250))
        return (len(hs), got, weights)

    def market_one(row):
        rid = str(row.get('id') or '')
        if not rid:
            return (rid, False)
        try:
            d = snapshot(rid)
            if not _bootstrap_display_ready(d):
                try:
                    _hydrate_fast_card_now(rid, deep_history=False)
                except Exception as exc:
                    print('full-day card hydrate failed', rid, exc)
            body = odds_refresh(rid, 1)
            field = int((body or {}).get('fieldCount') or 0)
            got = int((body or {}).get('oddsCount') or 0)
            return (rid, bool(field and got == field))
        except Exception as exc:
            print('full-day market refresh failed', rid, exc)
            return (rid, False)
    market_workers = max(6, min(int(os.getenv('FULL_DAY_ODDS_WORKERS', '20')), 24, len(rows)))
    market_results = {}
    ex = ThreadPoolExecutor(max_workers=market_workers)
    futures = {ex.submit(market_one, r): str(r.get('id') or '') for r in rows}
    market_deadline = min(deadline - 5.0, time.time() + max(6.0, min(14.0, deadline - time.time() - 5.0)))
    try:
        done, _ = wait(list(futures), timeout=max(0.5, market_deadline - time.time()))
        for fut in done:
            rid = futures[fut]
            try:
                market_results[rid] = bool(fut.result()[1])
            except Exception:
                market_results[rid] = False
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    missing = []
    for r in rows:
        rid = str(r.get('id') or '')
        field, got, _ = live_coverage(snapshot(rid))
        if rid and field and (got < field):
            missing.append(r)
    if missing and time.time() < deadline - 2.5:
        retry_workers = max(4, min(int(os.getenv('FULL_DAY_ODDS_RETRY_WORKERS', '16')), 20, len(missing)))
        ex = ThreadPoolExecutor(max_workers=retry_workers)
        fs = [ex.submit(market_one, r) for r in missing]
        try:
            wait(fs, timeout=max(0.5, min(4.0, deadline - time.time() - 2.0)))
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    nowj = _now_jst()
    nowm = nowj.hour * 60 + nowj.minute
    focus = []
    for r in rows:
        st = _race_minutes_server(r)
        remain = st - nowm if st < 9999 else 9999
        if -45 <= remain <= 240 or not _bootstrap_analysis_ready(snapshot(str(r.get('id') or ''))):
            focus.append(r)
    focus.sort(key=lambda r: abs((_race_minutes_server(r) if _race_minutes_server(r) < 9999 else nowm + 9999) - nowm))
    focus = focus[:max(12, min(28, len(focus)))]

    def finish_one(row):
        rid = str(row.get('id') or '')
        if not rid:
            return None
        try:
            st = _race_minutes_server(row)
            if st < 9999 and nowm >= st + 2 and (not _snapshot_final(snapshot(rid))):
                try:
                    _refresh_result_fast(rid)
                except Exception:
                    pass
            try:
                _build_fast_diagnosis_snapshot(rid, allow_network=False, deep_context=False)
            except Exception as exc:
                print('focused diagnosis rebuild failed', rid, exc)
            d = snapshot(rid)
            return _compact_display_snapshot(d) if d else None
        except Exception as exc:
            print('focused live rebuild failed', rid, exc)
            return None
    if focus and time.time() < deadline - 1.2:
        workers = max(4, min(10, len(focus)))
        ex = ThreadPoolExecutor(max_workers=workers)
        fs = [ex.submit(finish_one, r) for r in focus]
        try:
            wait(fs, timeout=max(0.4, deadline - time.time() - 1.0))
        finally:
            ex.shutdown(wait=False, cancel_futures=True)
    out = _assemble_day_bundle(date, allow_network_fill=False)
    if out.get('displayComplete'):
        try:
            DAY_BUNDLES.put(date, out, True)
        except Exception:
            pass
    dc_ready = 0
    for d in out.get('details', []) or []:
        try:
            hh = _data_core_store_health(d, set(), 'force-day')
            if all(((hh.get(k) or {}).get('status') == 'ready' for k in ('card', 'history', 'odds', 'body_weight', 'environment', 'analysis'))):
                dc_ready += 1
        except Exception as exc:
            print('data core force health failed', (d or {}).get('id'), exc)
    out['dataCore'] = {'version': ARVEXQ_DATA_CORE_VERSION, 'readyRaceCount': dc_ready, 'raceCount': len(out.get('races') or [])}
    odds_ready = 0
    odds_partial = 0
    odds_missing = []
    for d in out.get('details', []) or []:
        hs = [h for h in d.get('horses') or [] if not h.get('scratched') and int(h.get('horseNumber') or 0) > 0]
        got = sum((1 for h in hs if float(h.get('winOdds') or 0) > 0))
        if hs and got == len(hs):
            odds_ready += 1
        elif hs and got:
            odds_partial += 1
            odds_missing.append(str(d.get('id') or ''))
        elif hs:
            odds_missing.append(str(d.get('id') or ''))
    out['oddsReadyCount'] = odds_ready
    out['oddsPartialCount'] = odds_partial
    out['oddsMissingRaceIds'] = odds_missing
    out['forceLiveRefresh'] = True
    out['forceElapsedMs'] = int((time.time() - started) * 1000)
    with _site_bootstrap_lock:
        _site_force_cache[date] = (time.time(), dict(out))
        _site_bootstrap_cache[date] = (time.time(), dict(out))
    return out
