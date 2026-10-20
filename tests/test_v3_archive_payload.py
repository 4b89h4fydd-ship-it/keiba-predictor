"""Check real hash-verified originals rather than trusting only their manifest."""
import json
from pathlib import Path
import pytest

from arvexq.v3.audit.payload import verify_saved_payload, sample_saved_payloads
from scripts.arvexq_v3_archive_audit import ARCHIVE, audit_days


@pytest.mark.parametrize("race_id", [
    "jra-2026-10-18-京都-05",
    "nar-2026-10-18-高知-01",
])
def test_existing_saved_original_digest_and_roster(race_id):
    day = "2026-10-18"
    card = json.loads((ARCHIVE / "racecards" / (day + ".json")).read_text())
    manifest = json.loads((ARCHIVE / "saved-snapshots" / (day + ".json")).read_text())
    item = next(row for row in card["races"] if row["id"] == race_id)
    report = verify_saved_payload(ARCHIVE / "saved-snapshots", item, manifest["races"][race_id])
    assert report["hashVerified"] and report["raceId"] == race_id
    assert report["rosterCount"] == item["fieldSize"]
    assert report["fullCareerVerified"] is False
    assert report["predictionStatus"] == "not-implemented"


def test_tampering_manifest_digest_is_rejected():
    day = "2026-10-18"
    card = json.loads((ARCHIVE / "racecards" / (day + ".json")).read_text())
    row = next(x for x in card["races"] if x["id"] == "jra-2026-10-18-京都-05")
    with pytest.raises(ValueError):
        verify_saved_payload(ARCHIVE / "saved-snapshots", row,
                             {"sha256": "0" * 64, "file": "0" * 64 + ".json", "bytes": 53_138, "horses": 5})


def test_manifest_sample_counts_remain_bounded_and_nonforecast():
    report = audit_days(days=7, samples_per_circuit=1, end_date="2026-10-18")
    sample = report["savedPayloadSample"]
    assert sample["verifiedPayloads"] == sample["sampledPayloads"]
    assert sample["sampledPayloads"] == 10
    assert sample["failures"] == []
    assert sample["fullCareerVerified"] is False
    assert not any("tickets" in str(z) or "marks" in str(z) for z in sample["samples"])
