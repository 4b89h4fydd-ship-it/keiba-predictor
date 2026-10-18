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
    assert len(calls) == 3
    assert "details=1" in calls[-1]
