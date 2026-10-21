"""Offline integration contracts for the Stage 5 item 160/175 aliases.

Fixtures are synthetic and are not assertions about live JRA/NAR data.
No external HTTP calls, cache writes, or deployment paths are involved.
"""
from collections import Counter
import json
from urllib.error import HTTPError
from urllib.parse import quote

import pytest

from arvexq.components.item_160 import d1_day_readback as retry_box
from arvexq.components.item_175 import d1_day_readback as error_box
from arvexq.ingest import d1_day_readback as original
from arvexq.ingest.full_snapshot_codec import pack_detail

DAY = "2026-10-12"
BASE = "https://example.invalid"


def _overview(ids):
    return {"ok": True, "date": DAY, "races": [{"id": rid} for rid in ids]}


@pytest.mark.parametrize("race_id", ["jra-2026-10-12-京都-01", "nar-2026-10-12-佐賀-01"])
def test_both_circuits_preserve_the_same_existing_readback(race_id):
    calls = []
    race = {"id": race_id, "date": DAY, "horses": [{"horseNumber": 1, "name": "sample"}]}

    def fetch(url):
        calls.append(url)
        if url.endswith("/api/day?date=2026-10-12&details=0"):
            return _overview([race_id])
        if url == BASE + "/api/race/" + quote(race_id, safe=""):
            return {"ok": True, "detail": race}
        raise AssertionError("unexpected fetch path: " + url)

    result = retry_box.read_day(BASE, DAY, fetch=fetch)
    assert result["details"] == [race]
    assert result["readbackSources"] == {race_id: "full"}
    assert result["readErrors"] == []
    assert len(calls) == 2
    assert len(set(calls)) == 2
    assert retry_box.read_day is error_box.read_day is original.read_day


@pytest.mark.parametrize("code", [404, 503])
def test_fallback_is_the_existing_display_path_only(code):
    race_id = "nar-2026-10-12-佐賀-01"
    path = BASE + "/api/race/" + quote(race_id, safe="")
    calls = Counter()

    def fetch(url):
        calls[url] += 1
        if url.endswith("/api/day?date=2026-10-12&details=0"):
            return _overview([race_id])
        if url == path:
            raise HTTPError(url, code, "unavailable", {}, None)
        if url == path + "?view=display":
            return {"ok": True, "detail": {"id": race_id, "date": DAY, "horses": []}}
        raise AssertionError(url)

    result = error_box.read_day(BASE, DAY, fetch=fetch)
    assert result["readErrors"] == []
    assert result["readbackSources"] == {race_id: "display"}
    assert all(n == 1 for n in calls.values())
    assert len(calls) == 3


def test_non_retryable_per_race_error_is_explicit_without_extra_fetch():
    race_id = "jra-2026-10-12-京都-01"
    calls = []

    def fetch(url):
        calls.append(url)
        if "/api/day?" in url:
            return _overview([race_id])
        raise HTTPError(url, 403, "forbidden", {}, None)

    result = error_box.read_day(BASE, DAY, fetch=fetch)
    assert result["details"] == []
    assert result["readbackSources"] == {}
    assert len(result["readErrors"]) == 1
    assert result["readErrors"][0]["raceId"] == race_id
    assert "HTTPError" in result["readErrors"][0]["error"]
    assert len(calls) == 2


def test_duplicate_day_race_id_rejected_before_details():
    race_id = "nar-2026-10-12-佐賀-01"
    calls = []

    def fetch(url):
        calls.append(url)
        return _overview([race_id, race_id])

    with pytest.raises(ValueError, match="duplicate race summary identity"):
        retry_box.read_day(BASE, DAY, fetch=fetch)
    assert len(calls) == 1


def test_existing_archive_restore_keeps_original_prediction_and_bets():
    race_id = "jra-2026-10-12-京都-01"
    original_detail = {
        "id": race_id, "date": DAY,
        "horses": [{"horseNumber": 1, "pastRaces": [{"date": "2026-10-01", "finish": 2}]}],
        "preRacePrediction": {"frozen": True, "horses": [{"horseNumber": 1, "mark": "◎"}]},
        "preRaceBet": {"kind": "3連単", "items": [[1, 2, 3]]},
        "result": {"status": "確定", "payouts": [{"kind": "単勝", "amount": 300}]},
    }
    packed = pack_detail(original_detail)

    def fetch(url):
        if "/api/day?" in url:
            return _overview([race_id])
        return {"ok": True, "detail": packed}

    got = error_box.read_day(BASE, DAY, fetch=fetch)
    assert got["readErrors"] == []
    assert got["details"] == [original_detail]
    assert got["details"][0]["preRaceBet"] == original_detail["preRaceBet"]


def test_wrong_identity_fails_closed_and_is_counted():
    race_id = "jra-2026-10-12-京都-01"

    def fetch(url):
        if "/api/day?" in url:
            return _overview([race_id])
        return {"ok": True, "detail": {"id": race_id, "date": "2026-10-13"}}

    got = retry_box.read_day(BASE, DAY, fetch=fetch)
    assert got["details"] == []
    assert got["readErrors"][0]["raceId"] == race_id
    assert "race date mismatch" in got["readErrors"][0]["error"]


def test_corrupt_json_not_accepted_as_success():
    calls = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _limit):
            return b"not JSON"

    def opener(request, timeout):
        calls.append(request.full_url)
        return Response()

    with pytest.raises(json.JSONDecodeError):
        retry_box.get_json(BASE, opener=opener, sleeper=lambda _: None)
    assert calls == [BASE]

