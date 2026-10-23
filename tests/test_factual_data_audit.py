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

def test_banei_invalid_weight_not_accepted_as_flat_weight():
    detail = {"id": "nar-2026-10-19-帯広ば-01", "date": "2026-10-19",
              "track": "帯広ば", "analysisMode": "ばんえい",
              "horses": [{"horseNumber": 1, "name": "実測異常馬",
                          "carriedWeight": 59, "bodyWeight": 101}]}
    bundle = {"date": "2026-10-19", "races": [{"id": detail["id"]}],
              "details": [detail], "readErrors": []}
    before = deepcopy(bundle)
    report = audit_day(bundle)
    invalid = [row for row in report["validationErrors"]
               if row.get("error") == "invalid banei weight"]
    assert {row["field"] for row in invalid} == {"bodyWeight", "carriedWeight"}
    assert bundle == before


def test_flat_weight_55_remains_legal():
    detail = {"id": RID, "date": DAY, "track": "名古屋",
              "horses": [{"horseNumber": 1, "name": "平地馬",
                          "carriedWeight": 55, "bodyWeight": 450}]}
    bundle = {"date": DAY, "races": [{"id": RID}],
              "details": [detail], "readErrors": []}
    report = audit_day(bundle)
    assert not any(row.get("error") == "invalid banei weight"
                   for row in report["validationErrors"])
