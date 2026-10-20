"""Stage 4: actual repository archives, plus tampering/missingness regression."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from arvexq.v3.audit.archive import audit_pair, summarize
from scripts.arvexq_v3_archive_audit import audit_days


def fixture():
    r = {"id": "nar-2026-10-17-高知-01", "date": "2026-10-17",
         "circuit": "地方", "track": "高知", "fieldSize": 1,
         "horses": [{"horseNumber": 1, "frameNumber": 1, "name": "A",
                     "sex": "牡", "age": 5, "jockey": "騎手", "carriedWeight": 56}]}
    d = "a" * 64
    card = {"version": "arvexq-static-entry-v1", "date": r["date"], "raceCount": 1, "races": [r]}
    manifest = {"version": "arvexq-saved-snapshots-v1", "date": r["date"],
                "races": {r["id"]: {"file": d + ".json", "sha256": d,
                                    "bytes": 120, "horses": 1}}}
    return card, manifest


def test_actual_last_seven_days_are_reproducible_offline():
    result = audit_days(days=7, end_date="2026-10-18")
    assert result["start"] == "2026-10-12"
    assert result["end"] == "2026-10-18"
    assert result["racecards"] == 423
    assert result["manifestEntries"] == 423
    assert result["circuits"]["jra"]["races"] == 96
    assert result["circuits"]["jra"]["runnerRows"] == 1242
    assert result["circuits"]["nar"]["races"] == 327
    assert result["circuits"]["nar"]["runnerRows"] == 3415
    assert result["circuits"]["nar"]["missingByField"]["carriedWeight"] == 29
    assert result["structuralProblems"] == 0
    assert result["proofLimits"]["officialTotalRosterComparison"] == "not-performed"
    assert result["proofLimits"]["fullPastRunsCoverage"] == "not-measured"
    assert result["predictionStatus"] == "not-implemented"


def test_missing_banei_weights_are_observed_not_fabricated():
    result = audit_days(days=7, end_date="2026-10-18")
    rows = [row for day in result["dates"] for row in day["missingExamples"]]
    assert len(rows) == 29
    assert all(row["field"] == "carriedWeight" and "帯広ば" in row["raceId"] for row in rows)
    assert len({row["raceId"] for row in rows}) == 3


def test_manifest_mismatch_flagged_and_does_not_change_source():
    card, manifest = fixture()
    unchanged = deepcopy((card, manifest))
    good = audit_pair(card, manifest)
    assert good["integrity"] == "manifest-consistent"
    assert good["snapshotPayloadHashesVerified"] is False
    manifest["races"][card["races"][0]["id"]]["horses"] = 2
    bad = audit_pair(card, manifest)
    assert bad["problems"] == [{"code": "snapshot-manifest-runner-count-mismatch", "raceId": card["races"][0]["id"]}]
    assert card == unchanged[0]


def test_duplicate_runner_identity_and_bad_hash_filename_reported():
    c, m = fixture()
    c["races"][0]["horses"].append(deepcopy(c["races"][0]["horses"][0]))
    x = audit_pair(c, m)
    codes = {z["code"] for z in x["problems"]}
    assert "invalid-or-duplicate-runner-number" in codes
    assert "card-fieldsize-mismatch" in codes
    assert "snapshot-manifest-runner-count-mismatch" in codes
    c, m = fixture()
    m["races"][c["races"][0]["id"]]["file"] = "not_the_digest.json"
    assert "invalid-snapshot-filename" in {r["code"] for r in audit_pair(c, m)["problems"]}


def test_missing_field_counts_do_not_mark_past_runs_or_official_coverage_complete():
    c, m = fixture()
    c["races"][0]["horses"][0]["carriedWeight"] = None
    r = audit_pair(c, m)
    assert r["circuits"]["nar"]["missingByField"] == {"carriedWeight": 1}
    assert r["pastRunsCoverageVerified"] is False
    assert r["officialAllRacesVerified"] is False
    assert summarize([r])["structuralProblems"] == 0


def test_unknown_archive_schema_rejected():
    c, m = fixture()
    c["version"] = "nonexistent"
    with pytest.raises(ValueError, match="schema"):
        audit_pair(c, m)


def test_unpaired_newest_racecard_does_not_displace_verified_saved_week(tmp_path):
    from scripts.arvexq_v3_archive_audit import audit_days
    root = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"
    (tmp_path / "racecards").mkdir()
    (tmp_path / "saved-snapshots").mkdir()
    for day in ("2026-10-17", "2026-10-18"):
        (tmp_path / "racecards" / (day + ".json")).write_bytes(
            (root / "racecards" / (day + ".json")).read_bytes())
        (tmp_path / "saved-snapshots" / (day + ".json")).write_bytes(
            (root / "saved-snapshots" / (day + ".json")).read_bytes())
    (tmp_path / "racecards" / "2026-10-19.json").write_text("{}")
    report = audit_days(directory=tmp_path, days=2)
    assert report["start"] == "2026-10-17"
    assert report["end"] == "2026-10-18"
    assert report["dateCount"] == 2
    with pytest.raises(ValueError, match="insufficient"):
        audit_days(directory=tmp_path, days=3)
