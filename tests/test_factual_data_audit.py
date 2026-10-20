"""Readback identity, compressed evidence, gaps and future-history contracts."""
from copy import deepcopy
import io
import json
import urllib.error
import pytest

from arvexq.ingest.d1_day_readback import get_json, read_day
from arvexq.ingest.full_snapshot_codec import pack_detail
from arvexq.ingest.career_transport import pack_horse
from arvexq.quality.fact_audit import audit_day, observed

DAY = '2026-10-15'
RID = 'nar-2026-10-15-名古屋-01'


def test_day_reader_uses_small_routes_and_restores_complete_originals():
    original = {'id': RID, 'date': DAY, 'horses': [{'horseNumber': 2,
                 'allPastRuns': [{'date': '2026-09-01', 'finish': 2}]}]}
    calls = []
    def fetch(url):
        calls.append(url)
        return ({'ok': True, 'date': DAY, 'races': [{'id': RID}]} if '/api/day?' in url
                else {'ok': True, 'detail': pack_detail(original)})
    result = read_day('https://unit.test', DAY, fetch=fetch)
    assert result['details'] == [original] and result['readErrors'] == []
    assert 'details=0' in calls[0] and all('details=1' not in url for url in calls)


@pytest.mark.parametrize('code', [404,503])
def test_same_api_display_fallback_is_explicit_and_does_not_fabricate_missing_detail(code):
    def fetch(url):
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY, 'races': [{'id': RID}]}
        if 'view=display' not in url:
            raise urllib.error.HTTPError(url, code, 'unavailable legacy route', {}, None)
        return {'ok': True, 'detail': {'id': RID, 'date': DAY, 'horses': []}}
    result = read_day('https://unit.test', DAY, fetch=fetch)
    assert result['readbackSources'] == {RID: 'display'}
    assert audit_day(result)['displayFallbackRaces'] == 1


def test_partial_day_retains_real_records_and_records_the_failed_race():
    second = RID[:-2] + '02'
    def fetch(url):
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY, 'races': [{'id': RID}, {'id': second}]}
        if url.endswith('02'):
            return {'ok': True, 'detail': {'id': second, 'date': DAY, 'horses': []}}
        raise urllib.error.URLError('source unavailable')
    result = read_day('https://unit.test', DAY, fetch=fetch)
    assert [detail['id'] for detail in result['details']] == [second]
    assert result['readErrors'][0]['raceId'] == RID
    assert not audit_day(result)['allRaceReadsVerified']


@pytest.mark.parametrize('kind', ['identity', 'date', 'digest'])
def test_invalid_originals_remain_explicit_read_failures(kind):
    detail = {'id': RID, 'date': DAY, 'horses': []}
    if kind == 'identity': detail['id'] = 'other'
    if kind == 'date': detail['date'] = '2026-10-14'
    detail = pack_detail(detail)
    detail['id'] = RID
    if kind == 'digest': detail['arvexqFullPayload']['sha256'] = '0' * 64
    def fetch(url):
        return ({'ok': True, 'date': DAY, 'races': [{'id': RID}]} if '/api/day?' in url
                else {'ok': True, 'detail': detail})
    result = read_day('https://unit.test', DAY, fetch=fetch)
    assert result['details'] == [] and len(result['readErrors']) == 1
    assert not audit_day(result)['allRaceReadsVerified']


def test_missing_fields_and_zero_weight_change_are_distinguished_without_mutation():
    horse = pack_horse({'horseNumber': 2, 'bodyWeightChange': 0,
                       'allPastRuns': [{'date': '2026-09-01', 'finish': 2}]}, DAY)
    bundle = {'date': DAY, 'races': [{'id': RID}],
              'details': [{'id': RID, 'date': DAY, 'horses': [horse]}], 'readErrors': []}
    before = deepcopy(bundle)
    result = audit_day(bundle)
    assert result['missingHorseFields']['bodyWeightChange'] == 0
    assert result['missingHorseFields']['frameNumber'] == 1
    assert result['observed']['observedPriorRuns'] == 1
    assert result['observed']['verifiedCareerArchives'] == 1
    assert bundle == before
    assert observed('bodyWeightChange', 0) and not observed('bodyWeight', 0)
    assert not observed('bodyWeightChange', float('nan'))


def test_future_history_and_duplicate_horses_are_validation_errors():
    bundle = {'date': DAY, 'races': [{'id': RID}], 'details': [
        {'id': RID, 'date': DAY, 'horses': [
            {'horseNumber': 1, 'allPastRuns': [{'date': DAY}]}, {'horseNumber': 1}]}]}
    result = audit_day(bundle)
    assert len(result['validationErrors']) == 2
    assert result['observed']['observedPriorRuns'] == 0


def test_fractional_and_out_of_range_identities_are_reported_without_rewriting():
    bundle = {'date': DAY, 'races': [{'id': RID}], 'details': [
        {'id': RID, 'date': DAY, 'horses': [
            {'horseNumber': 1.5}, {'horseNumber': 19, 'frameNumber': 9}]}]}
    before = deepcopy(bundle)
    result = audit_day(bundle)
    assert len(result['validationErrors']) == 3 and bundle == before


def test_transient_get_is_bounded_and_invalid_json_is_not_a_retry_success():
    calls, delays = [], []
    def opener(request, timeout):
        calls.append(request.get_method())
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 503, 'temporary', {}, None)
        return io.BytesIO(b'{"ok":true}')
    assert get_json('https://unit.test', opener=opener, sleeper=delays.append) == {'ok': True}
    assert calls == ['GET', 'GET'] and delays == [0.5]
    with pytest.raises(json.JSONDecodeError):
        get_json('https://unit.test', opener=lambda *_a, **_k: io.BytesIO(b'invalid'), sleeper=delays.append)


def test_cli_persists_only_factual_observations_and_waiting_method_status(monkeypatch, tmp_path):
    from scripts import arvexq_fact_data_audit as cli
    report = tmp_path / 'report.json'
    monkeypatch.setattr('sys.argv', ['audit', '--days', '1', '--end-date', DAY, '--report', str(report)])
    monkeypatch.setattr(cli, 'read_day', lambda *_: {
        'date': DAY, 'races': [{'id': RID}],
        'details': [{'id': RID, 'date': DAY, 'horses': [{'horseNumber': 1}]}]})
    assert cli.main() == 0
    saved = json.loads(report.read_text())
    assert saved['predictionLogicStatus'] == '予想ロジック仕様待ち'
    assert saved['days'][0]['observed']['horses'] == 1


def test_cli_writes_read_failures_and_returns_failure(monkeypatch, tmp_path):
    from scripts import arvexq_fact_data_audit as cli
    report = tmp_path / 'failed.json'
    monkeypatch.setattr('sys.argv', ['audit', '--days', '1', '--end-date', DAY, '--report', str(report)])
    def unavailable(*_args):
        raise OSError('day unavailable')
    monkeypatch.setattr(cli, 'read_day', unavailable)
    assert cli.main() == 1
    assert json.loads(report.read_text())['errors'] == 1


def test_out_of_range_frame_audit_retains_observed_value_and_runner_identity():
    bundle = {'date': DAY, 'races': [{'id': RID}], 'details': [
        {'id': RID, 'date': DAY, 'horses': [
            {'horseNumber': 12, 'frameNumber': 12, 'name': '観測馬'}]}]}
    before = deepcopy(bundle)
    result = audit_day(bundle)
    assert result['validationErrors'] == [{
        'raceId': RID, 'horseNumber': 12, 'frameNumber': 12,
        'horseName': '観測馬', 'error': 'frame number outside 1..8'}]
    assert bundle == before


def test_same_named_runner_across_races_is_flagged_without_mutating_facts():
    second = RID[:-2] + "02"
    bundle = {"date": DAY, "races": [{"id": RID}, {"id": second}],
              "details": [
                  {"id": RID, "date": DAY, "horses": [
                      {"name": "重複馬", "horseNumber": 12, "frameNumber": 7}]},
                  {"id": second, "date": DAY, "horses": [
                      {"name": "重複馬", "horseNumber": 12, "frameNumber": 7},
                      {"name": "別馬", "horseNumber": 3, "frameNumber": 2}]}]}
    before = deepcopy(bundle)
    result = audit_day(bundle)
    assert result["validationErrors"] == [
        {"raceId": second, "otherRaceId": RID, "horseName": "重複馬",
         "horseNumber": 12, "error": "same runner name in multiple races on day"}]
    assert bundle == before


def test_same_named_runner_single_race_not_reported_as_cross_race():
    bundle = {"date": DAY, "races": [{"id": RID}],
              "details": [{"id": RID, "date": DAY, "horses": [
                  {"name": "重複馬", "horseNumber": 12, "frameNumber": 7}]}]}
    assert audit_day(bundle)["validationErrors"] == []


def test_audit_checks_actual_pwa_display_and_preserves_update_timestamps():
    row = {'id': RID, 'date': DAY, 'circuit': '地方',
           'track': '名古屋', 'raceNumber': 1,
           'horses': [{'horseNumber': 2, 'name': '観測馬',
                       'allPastRuns': [{'date': '2026-09-01', 'finish': 2}]}]}
    calls = []
    def fetch(url):
        calls.append(url)
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY,
                    'races': [{'id': RID, 'updatedAtEpoch': 1790000000}]}
        return {'ok': True, 'detail': deepcopy(row), 'detail_updated_at': 1790000100}
    result = audit_day(read_day('https://unit.test', DAY, fetch=fetch,
                                verify_display=True))
    assert len(calls) == 3 and 'view=display' in calls[-1]
    assert result['displayParityErrors'] == []
    assert result['updateEvidence'] == [{
        'raceId': RID, 'summaryUpdatedAtEpoch': 1790000000,
        'detailUpdatedAtEpoch': 1790000100,
        'detailReadable': True, 'readbackSource': 'full'}]


def test_display_historical_loss_is_reported_without_changing_stored_facts():
    original = {'id': RID, 'date': DAY, 'horses': [
        {'horseNumber': 2, 'name': '観測馬',
         'allPastRuns': [{'date': '2026-09-01', 'finish': 2}]}]}
    def fetch(url):
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY, 'races': [{'id': RID}]}
        if 'view=display' in url:
            return {'ok': True, 'detail': {'id': RID, 'date': DAY,
                    'horses': [{'horseNumber': 2, 'name': '観測馬'}]},
                    'detail_updated_at': 1790000100}
        return {'ok': True, 'detail': deepcopy(original),
                'detail_updated_at': 1790000100}
    bundle = read_day('https://unit.test', DAY, fetch=fetch, verify_display=True)
    assert bundle['details'] == [original]
    assert bundle['displayParityErrors'][0]['reason'] == 'display_fact_mismatch'
    assert 'horses_or_prior_runs' in bundle['displayParityErrors'][0]['fields']


def test_failed_display_endpoint_is_visible_even_when_full_read_succeeds():
    def fetch(url):
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY, 'races': [{'id': RID}]}
        if 'view=display' in url:
            raise urllib.error.HTTPError(url, 503, 'temporarily unavailable', {}, None)
        return {'ok': True, 'detail': {'id': RID, 'date': DAY, 'horses': []}}
    bundle = read_day('https://unit.test', DAY, fetch=fetch, verify_display=True)
    assert len(bundle['details']) == 1
    assert bundle['readErrors'] == []
    assert bundle['displayParityErrors'][0]['reason'] == 'display_read_failed'


def test_legacy_full_route_fallback_is_not_mistaken_for_parity_success():
    def fetch(url):
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY, 'races': [{'id': RID}]}
        if 'view=display' in url:
            return {'ok': True, 'detail': {'id': RID, 'date': DAY, 'horses': []}}
        raise urllib.error.HTTPError(url, 404, 'not found', {}, None)
    bundle = read_day('https://unit.test', DAY, fetch=fetch, verify_display=True)
    assert bundle['readbackSources'][RID] == 'display'
    assert bundle['displayParityErrors'] == [
        {'raceId': RID, 'reason': 'full_route_unavailable'}]


def test_missing_prior_runs_are_not_guessed_to_be_verified_debuts():
    bundle = {'date': DAY, 'races': [{'id': RID}], 'details': [
        {'id': RID, 'date': DAY, 'horses': [
            {'horseNumber': 1, 'name': '未検証馬'},
            {'horseNumber': 2, 'name': '確認済馬',
             'debutNoHistory': True,
             'careerCoverage': {'state': 'complete-no-starts'}}]}]}
    result = audit_day(bundle)
    assert [(r['horseNumber'], r['reason']) for r in result['missingHistoryReasons']] == [
        (1, 'acquisition-unverified'), (2, 'verified-no-prior-start')]


def test_cli_reports_display_mismatch_as_a_failing_audit(monkeypatch, tmp_path):
    from scripts import arvexq_fact_data_audit as cli
    report = tmp_path / 'display-audit.json'
    monkeypatch.setattr('sys.argv', ['audit', '--days', '1', '--end-date', DAY,
                                    '--verify-display', '--report', str(report)])
    calls = []
    def read_mock(*_args, **kwargs):
        calls.append(kwargs)
        return {'date': DAY, 'races': [{'id': RID}],
                'details': [{'id': RID, 'date': DAY, 'horses': []}],
                'displayParityErrors': [{'raceId': RID, 'reason': 'display_read_failed'}]}
    monkeypatch.setattr(cli, 'read_day', read_mock)
    assert cli.main() == 1
    assert calls == [{'verify_display': True}]
    saved = json.loads(report.read_text())
    assert saved['errors'] == 1
    assert saved['days'][0]['displayParityErrors'][0]['reason'] == 'display_read_failed'


def test_display_does_not_hide_packed_unrenderable_snapshot():
    original = {'id': RID, 'date': DAY, 'horses': [
        {'horseNumber': 3, 'name': '観測馬',
         'recentRaces': [{'date': '2026-09-01', 'finish': 1}]}]}
    packed = pack_detail(original)
    def fetch(url):
        if '/api/day?' in url:
            return {'ok': True, 'date': DAY, 'races': [{'id': RID}]}
        return {'ok': True, 'detail': deepcopy(packed)}
    bundle = read_day('https://unit.test', DAY, fetch=fetch, verify_display=True)
    # The Python audit can decode it; the current browser consumes body.detail raw.
    assert bundle['details'] == [original]
    assert bundle['displayParityErrors'] == [
        {'raceId': RID, 'reason': 'display_packed_payload_unrenderable'}]


@pytest.mark.parametrize("reverse_order", [False, True])
def test_same_name_in_jra_and_nar_is_not_a_collision(reverse_order):
    # A shared spelling is not proof of lifetime identity across circuits.
    jra = {"id": f"jra-{DAY}-東京-01", "date": DAY,
           "circuit": "中央", "track": "東京", "raceNumber": 1,
           "horses": [{"name": "同名馬", "horseNumber": 1}]}
    nar = {"id": f"nar-{DAY}-大井-01", "date": DAY,
           "circuit": "地方", "track": "大井", "raceNumber": 1,
           "horses": [{"name": "同名馬", "horseNumber": 1}]}
    details = [nar, jra] if reverse_order else [jra, nar]
    bundle = {"date": DAY, "races": [{"id": d["id"]} for d in details],
              "details": details, "readErrors": []}
    unchanged = deepcopy(bundle)
    result = audit_day(bundle)
    assert result["validationErrors"] == []
    assert result["observed"]["horses"] == 2
    assert bundle == unchanged


def test_same_name_in_two_jra_races_remains_a_collision():
    first = {"id": f"jra-{DAY}-東京-01", "date": DAY,
             "circuit": "中央", "track": "東京", "raceNumber": 1,
             "horses": [{"name": "同名馬", "horseNumber": 1}]}
    second = {"id": f"jra-{DAY}-東京-02", "date": DAY,
              "circuit": "中央", "track": "東京", "raceNumber": 2,
              "horses": [{"name": "同名馬", "horseNumber": 7}]}
    bundle = {"date": DAY, "races": [{"id": first["id"]}, {"id": second["id"]}],
              "details": [first, second], "readErrors": []}
    before = deepcopy(bundle)
    assert audit_day(bundle)["validationErrors"] == [{
        "raceId": second["id"], "otherRaceId": first["id"],
        "horseName": "同名馬", "horseNumber": 7,
        "error": "same runner name in multiple races on day",
    }]
    assert bundle == before


def test_unknown_circuit_is_not_assigned_to_jra_or_nar_by_name():
    known = {"id": f"jra-{DAY}-東京-01", "date": DAY,
             "circuit": "中央", "track": "東京", "raceNumber": 1,
             "horses": [{"name": "同名馬", "horseNumber": 2}]}
    unknown = {"id": "unverified-race", "date": DAY, "track": "未知場",
               "horses": [{"name": "同名馬", "horseNumber": 2}]}
    bundle = {"date": DAY, "races": [{"id": known["id"]}, {"id": unknown["id"]}],
              "details": [known, unknown], "readErrors": []}
    original = deepcopy(bundle)
    assert audit_day(bundle)["validationErrors"] == []
    assert bundle == original
