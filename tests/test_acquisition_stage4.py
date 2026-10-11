"""Stage 4 source interfaces and baseline data-output comparisons."""
import ast
import copy
import hashlib
import importlib
import inspect
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import app
from acquisition_replay import BASELINE_TREE, RECORDS, ROOT, caches, compare

DATE = '2026-10-10'
DETAIL = {'id': 'nar-2026-10-10-大井-01', 'date': DATE, 'track': '大井',
          'raceNumber': 1, 'circuit': '地方', 'horses': [{'horseNumber': 1, 'name': '試験馬'}]}
ODDS = '<table><tr><th>馬番</th><th>単勝</th><th>人気</th><th>馬体重</th></tr>' \
       '<tr><td>1</td><td>3.5</td><td>2</td><td>480(+4)</td></tr></table>'
PAYOUT = '<table><tr><th>単勝</th><td>1</td><td>350円</td></tr></table>'


@pytest.mark.parametrize('record', RECORDS, ids=lambda r: r['name'])
def test_all_function_bodies_signatures_and_dependency_ports(record):
    original = next(n for n in BASELINE_TREE.body if n.name == record['name'])
    digest = hashlib.sha256(ast.dump(original, include_attributes=False).encode()).hexdigest()
    assert digest == record['ast_sha256']
    target = ast.parse((ROOT / record['after']).read_text())
    moved = next(n for n in target.body if isinstance(n, ast.FunctionDef) and n.name == record['name'])
    # The only signature additions are explicit keyword-only runtime ports.
    assert [a.arg for a in moved.args.kwonlyargs] == record['dependencies']
    moved.args.kwonlyargs = original.args.kwonlyargs
    moved.args.kw_defaults = original.args.kw_defaults
    assert ast.dump(moved, include_attributes=False) == ast.dump(original, include_attributes=False)
    adapter = getattr(app, record['name'])
    assert str(inspect.signature(adapter)) == str(inspect.signature(original_function(record['name'])))
    assert all(hasattr(app, name) for name in record['dependencies'])
    assert all(hasattr(app, name) for name in record.get('owned_state', []))


def original_function(name):
    from acquisition_replay import original_namespace
    return original_namespace(app)[name]


def test_acquisition_modules_import_without_app_network_storage_or_workers():
    modules = sorted({r['after'][:-3].replace('/', '.') for r in RECORDS})
    code = ('import importlib,sys,urllib.request,sqlite3,threading\n'
            'def fail(*a,**k): raise AssertionError("import-time side effect")\n'
            'urllib.request.urlopen=fail\nsqlite3.connect=fail\nthreading.Thread.start=fail\n'
            f'for name in {modules!r}: importlib.import_module(name)\n'
            'assert "app" not in sys.modules\n')
    subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True, timeout=20)
    for path in {r['after'] for r in RECORDS}:
        tree = ast.parse((ROOT / path).read_text())
        assert len((ROOT / path).read_text().splitlines()) < 500
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                       and n.func.id in ('exec', 'eval', 'globals') for n in ast.walk(tree))


@pytest.mark.parametrize('name,args,body,timeout', [
    ('_jra_request', ('https://jra.test/card', 'card/AA', 30), '競走馬', 4.5),
    ('_netkeiba_get', ('https://netkeiba.test/card', 1.25, 8), '競走馬', 1.25),
    ('_environment_http_get', ('https://jra.test/weather', 30), '天候 晴', 2.8),
    ('_fetch_json_url', ('https://feed.test/races', 5.0, 'fixture-token'), '{"horses":[]}', 5.0),
])
def test_transports_exact_headers_post_encoding_and_timeouts(name, args, body, timeout):
    result, calls = compare(app, name, args, responses=[body])
    assert result
    assert len(calls) == 1 and calls[0][-1] == timeout


@pytest.mark.parametrize('name,args', [
    ('_jra_request', ('https://jra.test/fail',)),
    ('_netkeiba_get', ('https://netkeiba.test/fail',)),
    ('_environment_http_get', ('https://jra.test/fail',)),
    ('_fetch_json_url', ('https://feed.test/fail',)),
])
def test_transport_failure_propagation_has_no_added_retry(name, args):
    _, calls = compare(app, name, args, responses=[TimeoutError('fixture timeout')], expected_error='TimeoutError')
    assert len(calls) == 1


@pytest.mark.parametrize('name,args,cache_name', [
    ('_jra_request', ('https://jra.test/cache', None, 30), '_jra_text_cache'),
    ('_netkeiba_get', ('https://netkeiba.test/cache', 4.0, 30), '_netkeiba_cache'),
    ('_environment_http_get', ('https://jra.test/cache', 30), '_environment_http_cache'),
])
def test_source_cache_hit_expiry_force_and_failed_fetch_are_independent(name, args, cache_name):
    cache = getattr(app, cache_name)
    saved = dict(cache)
    cache.clear()
    getter = getattr(app, name)
    try:
        from io import BytesIO
        with patch('urllib.request.urlopen', side_effect=lambda *a, **k: BytesIO(b'first')) as http, \
                patch('time.time', return_value=100):
            assert getter(*args) == 'first'
            assert getter(*args) == 'first'
            assert http.call_count == 1
        with patch('urllib.request.urlopen', side_effect=TimeoutError('unavailable')) as http, \
                patch('time.time', return_value=131):
            with pytest.raises(TimeoutError):
                getter(*args)
            assert http.call_count == 1
        with patch('urllib.request.urlopen', side_effect=lambda *a, **k: BytesIO(b'recovered')) as http, \
                patch('time.time', return_value=131):
            assert getter(*args) == 'recovered'
            assert http.call_count == 1
        if name != '_environment_http_get':
            forced = list(args)
            forced[-1] = 0
            with patch('urllib.request.urlopen', side_effect=lambda *a, **k: BytesIO(b'forced')) as http:
                assert getter(*forced) == 'forced'
                assert http.call_count == 1
    finally:
        cache.clear()
        cache.update(saved)


def test_jra_failure_does_not_block_netkeiba_or_poison_other_source_cache():
    from io import BytesIO
    before = [dict(c) for c in caches(app)]
    try:
        for cache in caches(app):
            cache.clear()
        with patch('urllib.request.urlopen', side_effect=TimeoutError('JRA unavailable')):
            with pytest.raises(TimeoutError):
                app._jra_request('https://jra.test/unavailable')
        with patch('urllib.request.urlopen', side_effect=lambda *a, **k: BytesIO(b'netkeiba available')):
            assert app._netkeiba_get('https://netkeiba.test/available') == 'netkeiba available'
        assert not app._jra_text_cache
        assert app._jra_cache_lock is not app._netkeiba_cache_lock
        assert app._jra_cache_lock is not app._nar_odds_cache_lock
    finally:
        for cache, old in zip(caches(app), before):
            cache.clear()
            cache.update(old)


@pytest.mark.parametrize('history', [False, True])
def test_licensed_feed_priority_and_full_career_normalized_output(history):
    race = {'date': DATE, 'track': '東京', 'raceNumber': 1, 'surface': '芝', 'title': '新馬',
            'horses': [{'name': '試験馬', 'recentRaces': [{'date': '2026-09-01'}] * 5,
                        'allPastRuns': [{'date': '2026-09-01'}] * 12}]}
    env = {'CENTRAL_FEED_URL': 'https://feed.test/current/{date}', 'CENTRAL_FEED_TOKEN': 'current',
           'CENTRAL_HISTORY_FEED_URL': 'https://feed.test/history', 'CENTRAL_HISTORY_FEED_TOKEN': 'history'}
    result, calls = compare(app, 'fetch_central_feed', (DATE, history),
                            responses=[json.dumps({'races': [race]})], env=env,
                            overrides={'fetch_jra_official': lambda *a: pytest.fail('licensed feed bypassed')})
    assert len(result[0]['horses'][0]['allPastRuns']) == 12
    assert len(result[0]['horses'][0]['recentRaces']) == 5
    assert calls[0][0] == ('https://feed.test/history?date=' + DATE if history else 'https://feed.test/current/' + DATE)


def test_no_feed_uses_jra_and_configured_feed_error_does_not_change_priority():
    env = {'CENTRAL_FEED_URL': '', 'CENTRAL_HISTORY_FEED_URL': ''}
    result, calls = compare(app, 'fetch_central_feed', (DATE,), env=env,
                            overrides={'fetch_jra_official': lambda d: [{'date': d, 'source': 'JRA公式'}]})
    assert result == [{'date': DATE, 'source': 'JRA公式'}] and not calls
    compare(app, 'fetch_central_feed', (DATE,), env={'CENTRAL_FEED_URL': 'https://feed.test'},
            responses=[TimeoutError('licensed unavailable')], expected_error='TimeoutError',
            overrides={'fetch_jra_official': lambda *a: pytest.fail('priority changed')})


@pytest.mark.parametrize('responses', [[ODDS], [TimeoutError('first source'), ODDS], ['', ODDS],
                                     [TimeoutError('a'), TimeoutError('b')]])
def test_nar_odds_fallback_order_empty_cache_policy_and_output(responses):
    result, calls = compare(app, '_nar_live_odds', ('大井', DATE, 1, True), responses=responses)
    assert 'KeibaWeb/TodayRaceInfo/OddsTanFuku?' in calls[0][0]
    if len(responses) == 2:
        assert 'KeibaWeb_IPAT/TodayRaceInfo/OddsTanFuku_ipat?' in calls[1][0]
    if ODDS in responses:
        assert result[1]['winOdds'] == 3.5 and result[1]['bodyWeight'] == 480
    else:
        assert result == {}


@pytest.mark.parametrize('responses', [[PAYOUT], [TimeoutError('first source'), PAYOUT], ['', '']])
def test_nar_payout_fallback_and_result_output(responses):
    result, calls = compare(app, '_fetch_nar_payouts_only', (DETAIL,), responses=responses)
    assert 'www.keiba.go.jp' in calls[0][0]
    if len(calls) > 1:
        assert 'sp.keiba.go.jp' in calls[1][0]
    if PAYOUT in responses:
        assert result[0] == [{'type': '単勝', 'combination': '1', 'amount': 350}]


@pytest.mark.parametrize('limit', [5, 100000])
def test_jra_profile_history_cutoff_and_full_career_limit(limit):
    header = '<tr>' + ''.join(f'<th>{h}</th>' for h in
        ['年月日', '競馬場', 'レース名', '距離', '馬場', '頭数', '馬番', '着順', '騎手', '斤量', '人気', 'タイム']) + '</tr>'
    rows = []
    for day in range(13, 0, -1):
        cells = [f'2026年9月{day}日', '東京', '障害未勝利', '障3000', '良', '12', '1', '2', '騎手', '60.0', '3', '3:20.0']
        rows.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    html = '<table>' + header + ''.join(rows) + '</table>'
    result, calls = compare(app, '_jra_profile_runs', ('horse/AA', '2026-09-13', limit), responses=[html])
    assert len(result) == (5 if limit == 5 else 12)
    assert all(r['date'] < '2026-09-13' for r in result)
    assert calls[0][-1] == 4.5


def test_jra_and_netkeiba_result_outputs_preserve_sectionals_and_payouts():
    header = ['着順', '枠', '馬番', '馬名', 'タイム', '推定上り', 'コーナー通過順位', '単勝人気', '単勝オッズ', '馬体重']
    html = '<p>確定 コース：1600 メートル（芝） 天候：晴 芝：良</p><h2>試験レース</h2><table>'
    html += '<tr>' + ''.join(f'<th>{h}</th>' for h in header) + '</tr>'
    for no in range(1, 4):
        values = [no, no, no, '試験馬' + str(no), '1:34.5', '34.0', '3-2', no, '3.5', '480(+4)']
        html += '<tr>' + ''.join(f'<td>{v}</td>' for v in values) + '</tr>'
    html += '</table>' + PAYOUT
    overrides = {'_jra_date_from_cname': lambda c: DATE, '_jra_any_track': lambda c: '東京',
                 '_jra_any_race_no': lambda c: 1}
    result, _ = compare(app, '_jra_parse_result', ('result/AA', {'date': DATE}), responses=[html], overrides=overrides)
    assert result['result']['status'] == '確定'
    assert result['result']['finishers'][0]['last3FSeconds'] == 34.0
    result, _ = compare(app, '_netkeiba_current_result', ({'netkeibaRaceId': '202605040101'},), responses=[html])
    assert len(result['finishers']) == 3 and result['payouts'][0]['amount'] == 350


def test_preexisting_nar_result_last3f_error_is_identical_and_not_silently_fixed():
    html = '<p>競走成績 確定</p><table><tr><th>着順</th><th>馬番</th><th>馬名</th><th>馬体重</th></tr>' \
           '<tr><td>1</td><td>1</td><td>試験馬</td><td>480(+4)</td></tr></table>'
    compare(app, '_nar_official_result_fast', (DETAIL,), responses=[html], expected_error='NameError')


@pytest.mark.parametrize('function,args,html', [
    ('_parse_nar_environment_html', (), '<p>天候：小雨 馬場状態：稍重</p>'),
    ('_parse_jra_environment_html', ('障害',), '<p>天候：晴 芝：良 ダート：重</p>'),
    ('_parse_nar_live_odds_html', (), ODDS),
    ('_parse_nar_official_card_html', (DETAIL,), '<table><tr><th>馬番</th><th>馬名</th><th>馬体重</th></tr>'
     '<tr><td>1</td><td>試験馬</td><td>480(+4)</td></tr></table>'),
])
def test_source_parsers_match_baseline(function, args, html):
    actual_args = (*args, html) if function == '_parse_nar_official_card_html' else (html, *args)
    result, calls = compare(app, function, actual_args)
    assert result and not calls
