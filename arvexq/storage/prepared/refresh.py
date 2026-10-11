"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _restore_saved_odds(detail: dict, *, PREPARED_STORE, RACEDB, ZoneInfo, datetime) -> dict:
    """Display-only odds must survive diagnosis/history/environment snapshot rebuilds."""
    if not isinstance(detail, dict):
        return detail
    race_id = str(detail.get('id') or '')
    if not race_id:
        return detail
    rows = []
    try:
        rows = RACEDB.odds_latest(race_id) or []
    except Exception:
        rows = []
    if not rows:
        try:
            previous, _ = PREPARED_STORE.get(race_id)
            if previous:
                rows = [{'horseNumber': h.get('horseNumber'), 'winOdds': h.get('winOdds'), 'popularity': h.get('popularity'), 'oddsSource': h.get('oddsSource') or previous.get('oddsSource')} for h in previous.get('horses') or [] if h.get('winOdds') not in (None, '')]
                if rows:
                    detail['oddsUpdatedAt'] = previous.get('oddsUpdatedAt') or detail.get('oddsUpdatedAt')
                    detail['oddsSource'] = previous.get('oddsSource') or detail.get('oddsSource')
        except Exception:
            pass
    if not rows:
        return detail
    by = {int(h.get('horseNumber') or 0): h for h in detail.get('horses') or []}
    latest = 0
    source = ''
    for z in rows:
        no = int(z.get('horseNumber') or 0)
        h = by.get(no)
        if not h:
            continue
        for k in ('winOdds', 'popularity'):
            if z.get(k) not in (None, ''):
                h[k] = z.get(k)
        if z.get('oddsSource'):
            h['oddsSource'] = z.get('oddsSource')
            source = z.get('oddsSource')
        latest = max(latest, int(z.get('capturedAt') or 0))
    if source:
        detail['oddsSource'] = source
    if latest:
        detail['oddsUpdatedAt'] = datetime.fromtimestamp(latest, ZoneInfo('Asia/Tokyo')).strftime('%H:%M:%S')
    return detail

def _refresh_result_fast(race_id: str, *, _acq_snapshots_results, _attach_nar_payouts, _compact_display_snapshot, _fast_local_race_detail, _jra_find_cname, _jra_parse_result, _jra_result_cname_from_card, _merge_result_fields, _nar_official_result_fast, _netkeiba_current_result, _prepared_get_fresh, _race_should_have_result, _racedb_get_fast, _store_fast_snapshot, central_race_detail, nar_race_detail) -> dict | None:
    return _acq_snapshots_results._refresh_result_fast(race_id, _attach_nar_payouts=_attach_nar_payouts, _compact_display_snapshot=_compact_display_snapshot, _fast_local_race_detail=_fast_local_race_detail, _jra_find_cname=_jra_find_cname, _jra_parse_result=_jra_parse_result, _jra_result_cname_from_card=_jra_result_cname_from_card, _merge_result_fields=_merge_result_fields, _nar_official_result_fast=_nar_official_result_fast, _netkeiba_current_result=_netkeiba_current_result, _prepared_get_fresh=_prepared_get_fresh, _race_should_have_result=_race_should_have_result, _racedb_get_fast=_racedb_get_fast, _store_fast_snapshot=_store_fast_snapshot, central_race_detail=central_race_detail, nar_race_detail=nar_race_detail)

def _prepare_race_snapshot(race_id: str, force: bool=False, manual: bool=False, *, NarSync, PREPARED_STORE, RACEDB, _apply_enrichment, _attach_evaluation_context, _attach_nar_payouts, _attach_stored_career, _compact_display_snapshot, _nar_sync_io_lock, _precompute_detail_metrics, _prepared_get_fresh, _racedb_get_fast, _restore_saved_odds, _schedule_detail_background_jobs, _schedule_full_history_harvest, _snapshot_final, _strip_excluded, _today_iso, central_race_detail, datetime, nar_race_detail, re) -> dict | None:
    hit = _prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    if hit and (str(hit.get('date') or '') < _today_iso() or _snapshot_final(hit)) and (not force):
        return hit
    if hit and (not force):
        return hit
    if manual and race_id.startswith('nar-'):
        match = re.match('^nar-(\\d{4}-\\d{2}-\\d{2})-', race_id)
        if match:
            target = datetime.strptime(match.group(1), '%Y-%m-%d')
            sync = NarSync()
            try:
                with _nar_sync_io_lock:
                    if match.group(1) == _today_iso():
                        sync.sync_daily(force=True)
                    else:
                        sync.sync_month(target.year, target.month, force=True)
            finally:
                sync.store.conn.close()
    detail = nar_race_detail(race_id) if race_id.startswith('nar-') else central_race_detail(race_id)
    if not detail:
        return None
    horses = detail.get('horses') if isinstance(detail.get('horses'), list) else []
    if not race_id.startswith('nar-') and int(detail.get('fieldSize') or 0) > 0 and (not horses) and (not detail.get('result')):
        return None
    if race_id.startswith('nar-'):
        detail = _attach_nar_payouts(detail)
    if hit and hit.get('analysis'):
        detail['analysis'] = hit['analysis']
    detail = _strip_excluded(_apply_enrichment(race_id, detail))
    detail = _attach_stored_career(detail)
    detail = _precompute_detail_metrics(_attach_evaluation_context(detail))
    detail = _restore_saved_odds(detail)
    detail.setdefault('preparedMeta', {}).pop('fastPartial', None)
    detail.setdefault('historySearch', {'status': 'prepared', 'monthsDone': 0, 'maxMonths': 0, 'coverage': {'totalHorses': len(detail.get('horses', [])), 'totalRuns': sum((len(h.get('recentRaces') or []) for h in detail.get('horses', [])))}, 'error': '', 'source': detail.get('source') or 'prepared'})
    try:
        RACEDB.upsert_race(detail)
        _schedule_full_history_harvest(detail)
    except Exception as exc:
        print('RaceDB snapshot write failed', race_id, exc)
    PREPARED_STORE.put(detail, force=bool(manual or force))
    display = _compact_display_snapshot(detail)
    if detail.get('date') == _today_iso() and (not _snapshot_final(detail)):
        _schedule_detail_background_jobs(race_id, detail)
    return display

def _store_fast_snapshot(detail: dict, *, PREPARED_STORE, RACEDB, _racedb_snapshot_usable, _restore_saved_odds) -> None:
    if not detail or not _racedb_snapshot_usable(detail):
        return
    detail = _restore_saved_odds(detail)
    try:
        PREPARED_STORE.put(detail, force=True)
    except Exception as exc:
        print('fast prepared save failed', detail.get('id'), exc)
    try:
        RACEDB.upsert_race(detail)
    except Exception as exc:
        print('fast RaceDB save failed', detail.get('id'), exc)
