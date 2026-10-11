"""Stage 5 responsibilities with explicit runtime dependencies."""
from __future__ import annotations
from pathlib import Path
from fastapi import Query

def _merge_live_market_rows(race_id: str, fresh_rows: list[dict], saved: dict | None=None, *, RACEDB) -> list[dict]:
    """Preserve the best known live fields per horse when a source returns a partial table.

    A live odds page can briefly omit one or more runners while updating.  Never let
    that sparse response erase previously captured odds/body weight for other horses.
    Fresh non-empty fields win; the latest RaceDB point and saved race snapshot fill gaps.
    """
    by_no: dict[int, dict] = {}
    saved = saved or {}
    for h in saved.get('horses') or []:
        try:
            no = int(h.get('horseNumber') or 0)
        except Exception:
            no = 0
        if not no:
            continue
        z = {'horseNumber': no}
        for k in ('winOdds', 'popularity', 'bodyWeight', 'bodyWeightChange', 'oddsForecast', 'referenceBodyWeight', 'referenceBodyWeightDate', 'status', 'scratched', 'oddsSource'):
            if h.get(k) not in (None, ''):
                z[k] = h.get(k)
        by_no[no] = z
    try:
        for h in RACEDB.odds_latest(race_id) or []:
            no = int(h.get('horseNumber') or 0)
            if not no:
                continue
            z = by_no.setdefault(no, {'horseNumber': no})
            for k in ('winOdds', 'popularity', 'oddsSource'):
                if z.get(k) in (None, '') and h.get(k) not in (None, ''):
                    z[k] = h.get(k)
    except Exception as exc:
        print('odds preserve read failed', race_id, exc)
    for h in fresh_rows or []:
        try:
            no = int(h.get('horseNumber') or 0)
        except Exception:
            no = 0
        if not no:
            continue
        z = by_no.setdefault(no, {'horseNumber': no})
        for k, v in h.items():
            if k == 'horseNumber':
                continue
            if v not in (None, ''):
                z[k] = v
    return [by_no[k] for k in sorted(by_no)]

def odds_refresh(race_id: str, force: int=Query(0), *, PREPARED_STORE, RACEDB, _fast_local_race_detail, _jra_find_cname, _jra_parse_race, _jra_program_lookup, _merge_live_market_rows, _nar_live_odds, _nar_netkeiba_preview_rows, _nar_official_card_rows_fast, _netkeiba_card_rows_fast, _netkeiba_current_result, _netkeiba_live_win_odds, _netkeiba_program_race_id, _now_jst, _prepared_get_fresh, _racedb_get_fast, _reference_weight_from_horse, _site_bootstrap_cache, _site_bootstrap_lock, _snapshot_final, _today_iso, re):
    saved = _prepared_get_fresh(race_id) or _racedb_get_fast(race_id)
    saved_has_odds = bool(saved and any((h.get('winOdds') not in (None, '') and float(h.get('winOdds') or 0) > 0 for h in saved.get('horses') or [])))
    saved_horses = saved.get('horses') or [] if saved else []
    saved_has_weights = bool(saved_horses and all((h.get('bodyWeight') not in (None, '') for h in saved_horses if not h.get('scratched'))))
    if saved and saved.get('date') != _today_iso() and saved_has_odds:
        return {'raceId': race_id, 'horses': saved_horses, 'oddsSource': saved.get('oddsSource') or '保存済み', 'storedInRaceDB': True, 'oddsUpdatedAt': saved.get('oddsUpdatedAt') or ''}
    if saved and _snapshot_final(saved) and saved_has_odds and saved_has_weights:
        return {'raceId': race_id, 'horses': saved_horses, 'oddsSource': saved.get('oddsSource') or '保存済み', 'storedInRaceDB': True, 'oddsUpdatedAt': saved.get('oddsUpdatedAt') or ''}
    horses = []
    source = ''
    if race_id.startswith('nar-'):
        m = re.match('^nar-(\\d{4}-\\d{2}-\\d{2})-(.+)-(\\d{2})$', race_id)
        if m:
            odds = _nar_live_odds(m.group(2), m.group(1), int(m.group(3)), bool(force))
            merged = {int(no): dict(z or {}) for no, z in odds.items()}
            if not merged or any((not (z or {}).get('bodyWeight') for z in merged.values())):
                try:
                    detail = dict(saved or {})
                    detail.update({'id': race_id, 'date': m.group(1), 'track': m.group(2), 'raceNumber': int(m.group(3))})
                    if not detail.get('horses'):
                        try:
                            qd = _fast_local_race_detail(race_id)
                            if qd:
                                detail = qd
                        except Exception:
                            pass
                    for h in _nar_official_card_rows_fast(detail):
                        no = int(h.get('horseNumber') or 0)
                        if not no:
                            continue
                        z = merged.setdefault(no, {})
                        for k in ('bodyWeight', 'bodyWeightChange', 'status', 'scratched'):
                            if z.get(k) in (None, '') and h.get(k) not in (None, ''):
                                z[k] = h.get(k)
                    if merged and (not odds):
                        source = 'NAR公式出馬表'
                except Exception as exc:
                    print('NAR official body weight fallback failed', race_id, exc)
            try:
                detail = dict(saved or {})
                detail.update({'id': race_id, 'date': m.group(1), 'track': m.group(2), 'raceNumber': int(m.group(3))})
                nk = _nar_netkeiba_preview_rows(detail, bool(force)) or {}
                for no, z0 in nk.items():
                    z = merged.setdefault(int(no), {})
                    official_live = bool(z.get('winOdds') and (not z.get('oddsForecast')))
                    if not official_live and z0.get('winOdds'):
                        z['winOdds'] = z0.get('winOdds')
                        z['popularity'] = z0.get('popularity')
                        z['oddsSource'] = z0.get('oddsSource')
                        z['oddsForecast'] = bool(z0.get('oddsForecast'))
                    for k in ('bodyWeight', 'bodyWeightChange'):
                        if z.get(k) in (None, '') and z0.get(k) not in (None, ''):
                            z[k] = z0.get(k)
                if nk and (not odds):
                    source = 'netkeiba予想オッズ'
            except Exception as exc:
                print('NAR netkeiba preview fallback failed', race_id, exc)
            if saved:
                saved_by = {int(h.get('horseNumber') or 0): h for h in saved.get('horses') or []}
                for no, h0 in saved_by.items():
                    z = merged.setdefault(no, {})
                    if not z.get('bodyWeight'):
                        rw, rd = _reference_weight_from_horse(h0)
                        if rw:
                            z['referenceBodyWeight'] = rw
                            z['referenceBodyWeightDate'] = rd
            if saved and _snapshot_final(saved):
                for f in (saved.get('result') or {}).get('finishers') or []:
                    no = int(f.get('horseNumber') or 0)
                    if not no:
                        continue
                    z = merged.setdefault(no, {})
                    for k in ('bodyWeight', 'bodyWeightChange', 'popularity', 'winOdds'):
                        if z.get(k) in (None, '') and f.get(k) not in (None, ''):
                            z[k] = f.get(k)
            for no, z in sorted(merged.items()):
                horses.append({'horseNumber': int(no), **{k: v for k, v in z.items() if v is not None}})
            if not source:
                source = 'NAR公式' if odds else next((str(z.get('oddsSource') or '') for z in merged.values() if z.get('oddsSource')), '') or ('NAR公式出馬表' if horses else '')
    else:
        mm = re.match('^jra-(20\\d{2}-\\d{2}-\\d{2})-([^\\-]+)-(\\d{2})$', race_id)
        detail = {}
        if mm:
            detail = _jra_program_lookup(mm.group(1), mm.group(2), int(mm.group(3))) or {'date': mm.group(1), 'track': mm.group(2), 'raceNumber': int(mm.group(3))}
            detail['netkeibaRaceId'] = detail.get('netkeibaRaceId') or _netkeiba_program_race_id(mm.group(1), mm.group(2), int(mm.group(3)))
            merged = {}
            try:
                cname = _jra_find_cname(mm.group(1), mm.group(2), int(mm.group(3)))
                if cname:
                    jr = _jra_parse_race(cname, supplement_profiles=False) or {}
                    for h in jr.get('horses', []) or []:
                        no = int(h.get('horseNumber') or 0)
                        if not no:
                            continue
                        z = merged.setdefault(no, {})
                        for k in ('winOdds', 'popularity', 'bodyWeight', 'bodyWeightChange', 'status', 'scratched'):
                            if h.get(k) not in (None, ''):
                                z[k] = h.get(k)
                    if any((float(h.get('winOdds') or 0) > 0 or h.get('bodyWeight') for h in jr.get('horses') or [])):
                        source = 'JRA公式'
            except Exception as exc:
                print('fast odds JRA failed', race_id, exc)
            try:
                nk = _netkeiba_live_win_odds(detail, bool(force)) or {}
                for no, z0 in nk.items():
                    z = merged.setdefault(int(no), {})
                    for k in ('winOdds', 'popularity', 'bodyWeight', 'bodyWeightChange', 'status', 'scratched'):
                        if z.get(k) in (None, '') and (z0 or {}).get(k) not in (None, ''):
                            z[k] = (z0 or {}).get(k)
            except Exception as exc:
                print('fast odds secondary fallback failed', race_id, exc)
            if not any((float((z or {}).get('winOdds') or 0) > 0 for z in merged.values())):
                try:
                    card_detail = dict(detail)
                    card_detail['id'] = race_id
                    for h in _netkeiba_card_rows_fast(card_detail):
                        no = int(h.get('horseNumber') or 0)
                        if not no:
                            continue
                        z = merged.setdefault(no, {})
                        for k in ('winOdds', 'popularity', 'bodyWeight', 'bodyWeightChange', 'status', 'scratched'):
                            if h.get(k) not in (None, ''):
                                z[k] = h.get(k)
                    if any((float((z or {}).get('winOdds') or 0) > 0 for z in merged.values())):
                        source = 'netkeiba出馬表'
                except Exception as exc:
                    print('fast odds card scrape failed', race_id, exc)
            if not any((float((z or {}).get('winOdds') or 0) > 0 for z in merged.values())):
                try:
                    result_detail = saved or detail or {}
                    nkres = _netkeiba_current_result(result_detail) or {}
                    for f in nkres.get('finishers', []) or []:
                        no = int(f.get('horseNumber') or 0)
                        if not no:
                            continue
                        z = merged.setdefault(no, {})
                        for k in ('winOdds', 'popularity', 'bodyWeight', 'bodyWeightChange'):
                            if f.get(k) not in (None, ''):
                                z[k] = f.get(k)
                    if any((float((z or {}).get('winOdds') or 0) > 0 for z in merged.values())):
                        source = 'netkeiba最終'
                except Exception as exc:
                    print('final odds result fallback failed', race_id, exc)
            for no, z in sorted(merged.items()):
                horses.append({'horseNumber': no, **z})
            if not source and horses:
                source = 'netkeiba'
    horses = _merge_live_market_rows(race_id, horses, saved)
    if not source:
        source = next((str(h.get('oddsSource') or '') for h in horses if h.get('oddsSource')), '')
    if horses:
        try:
            RACEDB.save_odds(race_id, horses, source)
        except Exception as exc:
            print('RaceDB odds save failed', race_id, exc)
        try:
            snapshot, _ = PREPARED_STORE.get(race_id)
            if snapshot:
                by_no = {int(h.get('horseNumber') or 0): h for h in horses}
                for h in snapshot.get('horses', []):
                    update = by_no.get(int(h.get('horseNumber') or 0), {})
                    for key in ('winOdds', 'popularity', 'bodyWeight', 'bodyWeightChange', 'oddsForecast', 'referenceBodyWeight', 'referenceBodyWeightDate', 'status', 'scratched'):
                        if update.get(key) is not None:
                            h[key] = update[key]
                    if update.get('oddsSource'):
                        h['oddsSource'] = update.get('oddsSource')
                snapshot['oddsSource'] = source
                snapshot['oddsUpdatedAt'] = _now_jst().strftime('%H:%M:%S')
                PREPARED_STORE.put(snapshot, force=True)
                try:
                    RACEDB.upsert_race(snapshot)
                except Exception:
                    pass
        except Exception as exc:
            print('odds snapshot update failed', exc)
        try:
            with _site_bootstrap_lock:
                _site_bootstrap_cache.pop(_today_iso(), None)
        except Exception:
            pass
    if not horses:
        try:
            stored = RACEDB.odds_latest(race_id) or []
            if stored:
                horses = stored
                source = next((str(x.get('oddsSource') or '') for x in stored if x.get('oddsSource')), '保存済み')
        except Exception:
            pass
    live = [h for h in horses if not h.get('scratched') and int(h.get('horseNumber') or 0) > 0]
    odds_count = sum((1 for h in live if float(h.get('winOdds') or 0) > 0))
    return {'raceId': race_id, 'horses': horses, 'oddsSource': source, 'oddsUpdatedAt': _now_jst().strftime('%H:%M:%S'), 'storedInRaceDB': bool(horses), 'fieldCount': len(live), 'oddsCount': odds_count, 'oddsComplete': bool(live) and odds_count == len(live)}
