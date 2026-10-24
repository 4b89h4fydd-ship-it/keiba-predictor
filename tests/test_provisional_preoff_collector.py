"""Read-only provisional pre-off research capture contracts."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import gzip
import json

import pytest

from scripts.arvexq_collect_provisional_preoff import (
    collect, provisional_capture, write_bundle, JST, API_BASE,
)


NOW = datetime(2026, 10, 18, 11, 30, tzinfo=JST)


def detail():
    return {
        "id": "nar-2026-10-18-園田-01", "date": "2026-10-18",
        "startTime": "11:55", "track": "園田", "circuit": "地方",
        "surface": "ダート", "distance": 1400, "raceNumber": 1,
        "horses": [
            {"horseNumber": n, "name": f"馬{n}", "age": 4,
             "preRacePrediction": {"mark":"◎"},
             "recentRaces": [{"date":"2026-10-01", "finish": n,
                              "distance":1400, "fieldSize":9, "track":"園田"}]}
            for n in (1, 2, 3, 4)
        ],
        "preRacePrediction": {"marks":["◎"],"tickets":[1]},
        "preRaceBet": {"items":[1]},
    }


def test_provisional_evidence_never_claims_verified_official_roster(tmp_path):
    source = detail()
    rec = provisional_capture(source, now=NOW)
    assert rec["eligibility"] == "provisional-not-officially-attested"
    assert rec["independentOfficialRoster"] is False
    assert rec["snapshot"]["horseCount"] == 4
    assert "preRacePrediction" in source
    assert "◎" not in json.dumps(rec, ensure_ascii=False)
    output = tmp_path / "bundle.gz"
    info = write_bundle({"records":[rec]}, output)
    assert json.loads(gzip.decompress(output.read_bytes()))["records"][0] == rec
    assert info["compressedBytes"] > 0
    with pytest.raises(FileExistsError):
        write_bundle({"records":[rec]}, output)


def test_cancelled_runner_excluded_and_no_partial_roster():
    row = detail()
    row["horses"][0]["scratched"] = True
    rec = provisional_capture(row, now=NOW)
    assert rec["activeHorseNumbers"] == [2, 3, 4]
    row["horses"][1]["name"] = ""
    with pytest.raises(ValueError, match="unnamed"):
        provisional_capture(row, now=NOW)


@pytest.mark.parametrize("change", [
    lambda x: x.update(result={"status":"確定"}),
    lambda x: x["horses"][0].update(currentResult=1),
    lambda x: x["horses"][0].update(horseNumber=2),
    lambda x: x.update(startTime="11:00"),
])
def test_refuses_postrace_or_corrupted_inputs(change):
    row = detail()
    change(row)
    with pytest.raises(ValueError):
        provisional_capture(row, now=NOW)


def test_read_only_collector_follows_existing_endpoints_only():
    row = detail()
    day = {"ok": True,"races":[{k:row[k] for k in ("id","date","startTime")}]}
    seen = []
    def fetch(url):
        seen.append(url)
        return day if "/api/day?" in url else {"ok": True, "detail": row}
    result = collect(now=NOW, fetch=fetch)
    assert result["captured"] == 1
    assert result["verifiedForTraining"] is False
    assert len(seen) == 2
    assert seen[0] == API_BASE + "/api/day?date=2026-10-18&details=0"
    assert "/api/race/" in seen[1]
    assert not any("/api/sync" in x for x in seen)


def test_mismatched_post_or_missing_current_detail_is_skipped():
    row = detail()
    day = {"ok":True,"races":[{k:row[k] for k in ("id","date","startTime")}]}
    future = dict(row, startTime="12:00")
    result = collect(now=NOW, fetch=lambda url:
                     day if "/api/day?" in url else {"detail":future})
    assert result["captured"] == 0
    assert len(result["failures"]) == 1
    assert "scheduled post changed" in result["failures"][0]["reason"]

def test_empty_results_placeholder_can_be_removed_before_snapshot():
    row = detail()
    row["result"], row["results"], row["payouts"] = {}, [], None
    record = provisional_capture(row, now=NOW)
    assert record["snapshot"]["horseCount"] == 4
    assert "result" not in record["snapshot"]
    row["result"] = {"status": "確定"}
    with pytest.raises(ValueError, match="non-empty post-race"):
        provisional_capture(row, now=NOW)


def test_fallback_uses_existing_day_detail_route_on_404():
    from urllib.error import HTTPError
    row = detail()
    overview = {"ok": True, "races": [
        {k: row[k] for k in ("id", "date", "startTime")}
    ]}
    calls = []
    def fetch(url):
        calls.append(url)
        if "details=0" in url:
            return overview
        if "/api/race/" in url:
            raise HTTPError(url, 404, "not found", {}, None)
        return {"ok": True, "details": [row]}
    result = collect(now=NOW, fetch=fetch)
    assert result["captured"] == 1
    assert result["failures"] == []
    assert len(calls) == 4
    assert "?view=display" in calls[2]
    assert "details=1" in calls[-1]

def test_existing_display_route_recovers_full_detail_without_day_fallback():
    from urllib.error import HTTPError
    from hashlib import sha256
    row = detail()
    overview = {"ok":True, "races":[{k: row[k] for k in ("id","date","startTime")}]}
    calls = []
    def fetch(url):
        calls.append(url)
        if "details=0" in url:
            return overview
        if url.endswith("?view=display"):
            return {"ok":True, "detail":row}
        if "/api/race/" in url:
            raise HTTPError(url, 404, "no legacy payload", {}, None)
        raise AssertionError("must not request the day fallback")
    report = collect(now=NOW, fetch=fetch)
    assert report["captured"] == 1
    rec = report["records"][0]
    assert rec["historyComplete"] is True
    assert rec["horsesWithPastRuns"] == 4
    core = {k:v for k,v in rec.items() if k != "recordHash"}
    expected = sha256(json.dumps(core, ensure_ascii=False, sort_keys=True,
                        separators=(",",":"), allow_nan=False).encode()).hexdigest()
    assert rec["recordHash"] == expected
    assert len(calls) == 3


def test_wrong_identity_on_display_does_not_pollute_other_race():
    row = detail()
    overview = {"ok":True, "races":[{k:row[k] for k in ("id","date","startTime")}]}
    wrong = dict(row, id="nar-2026-10-18-園田-02")
    def fetch(url):
        if "details=0" in url:
            return overview
        if "details=1" in url:
            return {"ok":True, "details":[wrong]}
        return {"ok":True, "detail":wrong}
    report = collect(now=NOW, fetch=fetch)
    assert report["captured"] == 0
    assert report["failures"][0]["reason"] == "no matching full race detail in existing API"


def test_no_past_runs_marked_incomplete_not_fabricated():
    row = detail()
    for horse in row["horses"]:
        horse.pop("recentRaces", None)
    rec = provisional_capture(row, now=NOW)
    assert rec["horsesWithPastRuns"] == 0
    assert rec["historyComplete"] is False


def test_existing_display_response_recovers_histories_hidden_by_compact_response():
    row = detail()
    overview = {"ok": True, "races": [
        {k: row[k] for k in ("id", "date", "startTime")}
    ]}
    shallow = json.loads(json.dumps(row))
    for horse in shallow["horses"]:
        horse.pop("recentRaces", None)
    calls = []

    def fetch(url):
        calls.append(url)
        if "details=0" in url:
            return overview
        if url.endswith("?view=display"):
            return {"ok": True, "detail": row}
        if "/api/race/" in url:
            return {"ok": True, "detail": shallow}
        raise AssertionError("full display history must avoid day fallback")

    result = collect(now=NOW, fetch=fetch)
    assert result["captured"] == 1
    assert result["failures"] == []
    assert result["records"][0]["historyComplete"] is True
    assert result["records"][0]["horsesWithPastRuns"] == 4
    assert result["verifiedForTraining"] is False
    assert len(calls) == 3


def test_existing_day_details_can_rescue_two_history_empty_race_responses():
    row = detail()
    overview = {"ok": True, "races": [
        {k: row[k] for k in ("id", "date", "startTime")}
    ]}
    shallow = json.loads(json.dumps(row))
    for horse in shallow["horses"]:
        horse.pop("recentRaces", None)
    calls = []

    def fetch(url):
        calls.append(url)
        if "details=0" in url:
            return overview
        if "details=1" in url:
            return {"ok": True, "details": [row]}
        return {"ok": True, "detail": shallow}

    result = collect(now=NOW, fetch=fetch)
    assert result["captured"] == 1
    assert result["records"][0]["horsesWithPastRuns"] == 4
    assert result["records"][0]["independentOfficialRoster"] is False
    assert result["verifiedForTraining"] is False
    assert len(calls) == 4
    assert "details=1" in calls[-1]
