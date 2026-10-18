"""Tests for independent observed-only source provenance handoff."""
from copy import deepcopy

from arvexq.ingest.source_provenance import observed_provenance
from arvexq.quality.fact_audit import audit_day


def test_provenance_preserves_observed_labels_without_guessing():
    detail = {"id": "jra-2026-10-18-京都-02", "source": "JRA公式",
              "sourceUrl": "https://www.jra.go.jp/test"}
    horse = {"name": "観測馬", "source": "netkeiba"}
    assert observed_provenance(detail, horse) == {
        "raceSource": "JRA公式",
        "raceSourceUrl": "https://www.jra.go.jp/test",
        "runnerSource": "netkeiba"}
    assert observed_provenance({}, {}) == {}


def test_factual_anomaly_preserves_source_evidence_without_editing_horse():
    rid = "jra-2026-10-18-京都-02"
    detail = {"id": rid, "date": "2026-10-18", "source": "JRA公式",
              "horses": [{"name": "異常馬", "horseNumber": 12,
                          "frameNumber": 12, "source": "external"}]}
    snapshot = deepcopy(detail)
    bundle = {"date": "2026-10-18", "races": [{"id": rid}], "details": [detail]}
    assert audit_day(bundle)["validationErrors"] == [{
        "raceId": rid, "horseNumber": 12, "frameNumber": 12, "horseName": "異常馬",
        "error": "frame number outside 1..8", "raceSource": "JRA公式",
        "runnerSource": "external"}]
    assert detail == snapshot


def test_provenance_values_bounded_and_non_string_ignored():
    data = {"source": "x" * 500, "sourceUrl": 5}
    assert observed_provenance(data, {}) == {"raceSource": "x" * 240}
