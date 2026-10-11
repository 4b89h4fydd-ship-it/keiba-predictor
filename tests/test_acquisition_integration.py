"""Acquisition → real SQLite → API and frozen prediction integration."""
import copy
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import patch

import app
import pytest
from fastapi.testclient import TestClient
from acquisition_replay import compare, original_namespace

DATE = '2026-10-10'


def central_row(title='未勝利', surface='芝'):
    career = [{'date': f'2026-09-{day:02}', 'track': '東京', 'raceNumber': 1,
               'distance': 1600, 'finish': 2, 'fieldSize': 12, 'source': '公式'} for day in range(12, 0, -1)]
    return {'id': f'jra-{DATE}-東京-01', 'date': DATE, 'track': '東京', 'raceNumber': 1,
            'title': title, 'distance': 1600, 'surface': surface, 'circuit': '中央',
            'startTime': '15:00', 'weather': '晴', 'condition': '良', 'fieldSize': 1,
            'horses': [{'horseNumber': 1, 'name': '中央試験馬', 'allPastRuns': career, 'recentRaces': career[:5]}]}


def seed_central(path, row):
    store = app.CentralStore(path)
    try:
        store.conn.execute('DELETE FROM central_races')
        store.conn.commit()
        store.upsert([copy.deepcopy(row)])
    finally:
        store.conn.close()


def seed_nar(path):
    store = app.NarStore(path)
    try:
        with store.conn:
            store.conn.execute('DELETE FROM races')
            store.conn.execute('DELETE FROM entries')
            for date in [DATE, '2026-09-01']:
                store.conn.execute('INSERT INTO races(track,date,race_no,title,distance,field_size,start_time) VALUES(?,?,?,?,?,?,?)',
                                   ('大井', date, 1, '地方試験レース', 1200, 3, '15:00'))
                for no in range(1, 4):
                    store.conn.execute('INSERT INTO entries(track,date,race_no,horse_no,name,finish,time_seconds) VALUES(?,?,?,?,?,?,?)',
                                       ('大井', date, 1, no, '地方試験馬' + str(no), no, 73.0 + no))
    finally:
        store.conn.close()


@pytest.mark.parametrize('title,surface', [('未勝利', '芝'), ('新馬', '芝'), ('障害未勝利', '障害')])
def test_central_detail_and_saved_payload_match_baseline_without_truncating_career(tmp_path, title, surface):
    path = tmp_path / 'central.sqlite3'
    row = central_row(title, surface)
    store_type = app.CentralStore

    def setup():
        seed_central(path, row)

    def capture():
        conn = app._new_conn(path)
        try:
            return [json.loads(r['payload']) for r in conn.execute('SELECT payload FROM central_races ORDER BY id')]
        finally:
            conn.close()

    ports = {'CENTRAL_DB_PATH': path, 'CentralStore': lambda: store_type(path),
             '_jra_program_lookup': lambda *a: None, '_netkeiba_program_race_id': lambda *a: '202605040101',
             '_race_should_have_result': lambda *a: False}
    result, calls = compare(app, 'central_race_detail', (row['id'],), overrides=ports, setup=setup, capture=capture)
    assert len(result['horses'][0]['allPastRuns']) == 12
    assert len(result['horses'][0]['recentRaces']) == 5
    assert result['surface'] == surface and not calls
    assert capture()[0]['title'] == title


def test_central_summary_source_failure_and_cached_result_are_independent(tmp_path):
    path = tmp_path / 'central.sqlite3'
    row = central_row()
    seed_central(path, row)
    ports = {'CENTRAL_DB_PATH': path, '_jra_program_summaries': lambda *a: [],
             '_netkeiba_race_summaries': lambda *a: [], 'CentralStore': lambda: pytest.fail('empty update')}
    result, calls = compare(app, 'central_race_summaries', (DATE, True, False), overrides=ports)
    assert result[0]['id'] == row['id'] and result[0]['horses'] == [] and not calls
    assert result[0]['fieldSize'] == 1


def test_nar_database_card_history_result_and_summary_match_baseline(tmp_path):
    path = tmp_path / 'nar.sqlite3'
    seed_nar(path)
    store_type = app.NarStore
    ports = {'DB_PATH': path, 'NarStore': lambda: store_type(path)}
    card, calls = compare(app, 'nar_race_detail', (f'nar-{DATE}-大井-01',), overrides=ports)
    assert not calls
    assert card['result']['status'] == '確定' and len(card['result']['finishers']) == 3
    assert card['horses'][0]['recentRaces'][0]['date'] == '2026-09-01'
    summary, _ = compare(app, 'nar_race_summaries', (DATE,), overrides=ports)
    assert summary[0]['horses'] == [] and summary[0]['result']['status'] == '確定'
    attached, _ = compare(app, '_nar_attach_recent_batch', (card, 5), overrides=ports)
    assert all(len(h['recentRaces']) == 1 for h in attached['horses'])


@pytest.mark.parametrize('circuit', ['中央', '地方'])
def test_races_api_uses_real_source_stores_and_isolates_unrelated_source_failure(tmp_path, circuit):
    central = tmp_path / 'central.sqlite3'
    nar = tmp_path / 'nar.sqlite3'
    seed_central(central, central_row())
    seed_nar(nar)
    with ExitStack() as stack:
        stack.enter_context(patch.object(app, 'CENTRAL_DB_PATH', central))
        stack.enter_context(patch.object(app, 'DB_PATH', nar))
        for name in ('_schedule_live_refresh', '_schedule_central_refresh', '_schedule_track_environment', '_schedule_prewarm'):
            stack.enter_context(patch.object(app, name, lambda *a, **k: None))
        stack.enter_context(patch.object(app, '_attach_local_volatility_to_summaries', lambda rows: rows))
        # Request both domains: one failing source must leave the other source visible.
        broken = 'nar_race_summaries' if circuit == '中央' else 'central_race_summaries'
        stack.enter_context(patch.object(app, broken, side_effect=RuntimeError('unrelated source unavailable')))
        stack.enter_context(patch('urllib.request.urlopen', side_effect=AssertionError('API must remain local')))
        old_cache = dict(app._race_list_cache)
        app._race_list_cache.clear()
        try:
            response = TestClient(app.app).get('/api/v1/races', params={'date': DATE, 'force': 1})
            assert response.status_code == 200
            assert response.json() and {r['circuit'] for r in response.json()} == {circuit}
            assert response.json()[0]['horses'] == []
        finally:
            app._race_list_cache.clear()
            app._race_list_cache.update(old_cache)


@pytest.mark.parametrize('circuit', ['中央', '地方'])
def test_race_detail_api_executes_extracted_local_snapshot_without_network(tmp_path, circuit):
    central = tmp_path / 'central.sqlite3'
    nar = tmp_path / 'nar.sqlite3'
    seed_central(central, central_row())
    seed_nar(nar)
    rid = f'jra-{DATE}-東京-01' if circuit == '中央' else f'nar-{DATE}-大井-01'
    with ExitStack() as stack:
        stack.enter_context(patch.object(app, 'CENTRAL_DB_PATH', central))
        stack.enter_context(patch.object(app, 'DB_PATH', nar))
        for name in ('_prepared_get_fresh', '_racedb_get_fast'):
            stack.enter_context(patch.object(app, name, lambda *a: None))
        stack.enter_context(patch.object(app, '_store_fast_snapshot', lambda *a: None))
        stack.enter_context(patch('urllib.request.urlopen', side_effect=AssertionError('first paint must remain local')))
        expected, calls = compare(app, '_fast_local_race_detail', (rid,))
        assert expected and not calls
        response = TestClient(app.app).get('/api/v1/race/' + rid)
        assert response.status_code == 200
        assert response.json()['id'] == rid and response.json()['horses']
        if circuit == '中央':
            assert len(response.json()['horses'][0]['recentRaces']) == 5
            # Display-only compaction does not alter the stored full career.
            conn = app._new_conn(central)
            try:
                stored = json.loads(conn.execute('SELECT payload FROM central_races').fetchone()['payload'])
                assert len(stored['horses'][0]['allPastRuns']) == 12
            finally:
                conn.close()


def test_source_network_wait_does_not_hold_another_sources_lock():
    entered = threading.Event()
    release = threading.Event()
    old_jra = dict(app._jra_text_cache)
    old_nk = dict(app._netkeiba_cache)

    def get(req, timeout):
        if req.full_url.startswith('https://jra.test/'):
            entered.set()
            assert release.wait(5)
            raise TimeoutError('JRA delayed')
        return io.BytesIO(b'other source available')

    app._jra_text_cache.clear()
    app._netkeiba_cache.clear()
    try:
        with patch('urllib.request.urlopen', get), ThreadPoolExecutor(max_workers=2) as pool:
            stalled = pool.submit(app._jra_request, 'https://jra.test/delayed')
            assert entered.wait(3)
            try:
                ready = pool.submit(app._netkeiba_get, 'https://netkeiba.test/ready')
                assert ready.result(timeout=2) == 'other source available'
                assert app._jra_cache_lock.acquire(blocking=False)
                app._jra_cache_lock.release()
            finally:
                release.set()
            with pytest.raises(TimeoutError):
                stalled.result(timeout=3)
    finally:
        app._jra_text_cache.clear()
        app._jra_text_cache.update(old_jra)
        app._netkeiba_cache.clear()
        app._netkeiba_cache.update(old_nk)


@pytest.mark.parametrize('circuit,limit', [('地方', 100000), ('中央', 10000)])
def test_full_career_harvest_retains_limits_and_isolates_each_horse_failure(circuit, limit):
    from types import SimpleNamespace
    import arvexq.ingest.history.harvest as harvest
    events = []
    runs = [{'date': f'2026-09-{n:02}', 'finish': 2} for n in range(1, 13)]

    class InlineThread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    class Bank:
        def _horse_key(self, horse):
            return horse['name']

        def source_updated(self, key):
            return 0

        def upsert_past_runs(self, horse, rows):
            events.append(('save', horse['name'], len(rows)))
            return len(rows)

        def mark_source(self, key, status, message):
            events.append(('source', key, status, message))

    def get_runs(name, cutoff, requested_limit):
        events.append(('fetch', name, cutoff, requested_limit))
        if name == 'broken':
            raise TimeoutError('one horse unavailable')
        return copy.deepcopy(runs)

    class Store:
        conn = SimpleNamespace(close=lambda: None)
        recent_races = staticmethod(get_runs)

    detail = {'id': 'harvest-test', 'date': DATE, 'circuit': circuit,
              'horses': [{'name': 'broken', '_jraHorseCname': 'broken'},
                         {'name': 'ready', '_jraHorseCname': 'ready'}]}
    ports = {'NarStore': Store, 'RACEDB': Bank(), '_jra_profile_runs': get_runs,
             'PREPARED_STORE': SimpleNamespace(get=lambda rid: (None, 0)),
             'threading': SimpleNamespace(Thread=InlineThread)}
    saved = set(app._full_history_running)
    try:
        with patch.object(harvest, 'threading', ports['threading']):
            result, calls = compare(app, '_schedule_full_history_harvest', (detail,), overrides=ports,
                                    setup=events.clear, capture=lambda: sorted(events))
        assert result is None and not calls
        assert ('save', 'ready', 12) in events
        assert all(e[-1] == limit for e in events if e[0] == 'fetch')
        assert any(e[0] == 'source' and e[2] == 'error' for e in events)
        assert any(e[0] == 'source' and e[2] == 'done' for e in events)
        assert 'harvest-test' not in app._full_history_running
    finally:
        app._full_history_running.clear()
        app._full_history_running.update(saved)


def test_nar_fast_hydration_continues_after_archive_and_result_failures():
    from types import SimpleNamespace
    stored = []

    class FailingSync:
        store = SimpleNamespace(conn=SimpleNamespace(close=lambda: None))

        def sync_month(self, *args, **kwargs):
            raise TimeoutError('archive unavailable')

    def broken_result(detail):
        raise TimeoutError('result unavailable')

    detail = {'id': f'nar-{DATE}-大井-01', 'date': DATE, 'track': '大井', 'raceNumber': 1,
              'circuit': '地方', 'horses': [{'horseNumber': 1, 'name': '試験馬'}]}
    ports = {'NarSync': FailingSync, '_today_iso': lambda: '2026-10-11',
             '_fast_local_race_detail': lambda rid: copy.deepcopy(detail),
             '_nar_result_should_be_available': lambda d: True, '_nar_official_result_fast': broken_result,
             '_nar_official_card_rows_fast': lambda d: [{'horseNumber': 1, 'bodyWeight': 480, 'bodyWeightChange': 4}],
             '_store_fast_snapshot': lambda d: stored.append(copy.deepcopy(d))}
    compare(app, '_hydrate_fast_card_now', (detail['id'], False), overrides=ports,
            setup=stored.clear, capture=lambda: stored)
    assert len(stored) == 1 and stored[0]['horses'][0]['bodyWeight'] == 480


@pytest.mark.parametrize('title,surface', [('新馬', '芝'), ('障害未勝利', '障害')])
def test_jra_card_output_and_debut_history_completeness_match_baseline(title, surface):
    course = '障害 芝' if surface == '障害' else '芝'
    # The existing parser checks 芝 before 障害; fixtures use 障 for its actual
    # dedicated obstacle branch. Preserve this rule rather than changing it.
    if surface == '障害':
        course = '障'
    html = f'<h2>{title}</h2><p>発走時刻：15時00分 コース：1600メートル（{course}） 天候 晴 芝 良</p>'
    html += '<table><thead><tr><th>馬番</th><th>馬名</th><th>性齢</th><th>前走</th></tr></thead><tbody>'
    html += '<tr><td>1</td><td>試験馬</td><td>牡2 55.0kg 騎手</td>' + '<td>未出走</td>' * 4 + '</tr></tbody></table>'
    ports = {'_jra_date_from_cname': lambda c: DATE, '_jra_track_from_cname': lambda c: '東京',
             '_jra_race_no_from_cname': lambda c: 1, '_jra_program_lookup': lambda *a: None,
             '_today_iso': lambda: '2026-10-11'}
    result, calls = compare(app, '_jra_parse_race', ('card/AA', True), responses=[html], overrides=ports)
    assert result['surface'] == surface
    assert result['horses'][0]['_jraCareerComplete']
    assert result['horses'][0]['recentRaces'] == [] and len(calls) == 1
