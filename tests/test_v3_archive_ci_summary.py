"""Stage 39: ensure CI summary describes failures without claiming official coverage."""
from scripts.arvexq_v3_full_archive_audit import summarize_for_ci, audit_exit_code


def test_ci_summary_aggregates_error_codes_and_unpaired_days():
    result = {
        "dateRange": ["2026-10-12", "2026-10-14"],
        "integrityScanRange": ["2026-10-12", "2026-10-15"],
        "expectedRacecards": 2,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": False,
        "circuits": {"jra": {"verified": 1}, "nar": {"verified": 0}},
        "errors": [
            {"code": "unpaired-saved-day"},
            {"code": "unpaired-saved-day"},
            {"code": "empty-saved-race-selection"},
        ],
        "unpairedSavedDays": [{"date": "2026-10-15", "filePresence": "manifest-only"}],
        "runnerEvidenceTriage": {
            "zeroObservedPriorRuns": 0,
            "byCircuitCategory": {},
            "missingCardCarriedWeight": 0,
            "missingWeightByState": {},
        },
    }
    summary = summarize_for_ci(result)
    assert summary["verificationByCircuit"] == {"jra": {"expected": 0, "verified": 1, "failed": 0}, "nar": {"expected": 0, "verified": 0, "failed": 0}}
    assert summary["circuitCountReconciliation"] == {"jra": False, "nar": True}
    assert summary["verificationCountsReconciled"] is False
    assert summary["errorCount"] == 3
    assert summary["errorCodes"] == {
        "empty-saved-race-selection": 1,
        "unpaired-saved-day": 2,
    }
    assert summary["integrityScanRange"] == ["2026-10-12", "2026-10-15"]
    assert summary["unpairedSavedDays"] == [{"date": "2026-10-15", "filePresence": "manifest-only"}]
    assert summary["allIndexedSavedOriginalsVerified"] is False
    assert "officialPublishedRacesVerified" not in summary


def test_ci_summary_reconciles_valid_circuit_totals():
    result = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "expectedRacecards": 3,
        "hashVerifiedRacecards": 2,
        "allIndexedSavedOriginalsVerified": False,
        "circuits": {
            "jra": {"expected": 2, "verified": 1, "failed": 1},
            "nar": {"expected": 1, "verified": 1, "failed": 0},
        },
        "errors": [{"code": "ValueError"}],
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {
            "zeroObservedPriorRuns": 0,
            "byCircuitCategory": {},
            "missingCardCarriedWeight": 0,
            "missingWeightByState": {},
        },
    }
    summary = summarize_for_ci(result)
    assert summary["circuitCountReconciliation"] == {"jra": True, "nar": True}
    assert summary["verificationCountsReconciled"] is True
    assert summary["verificationByCircuit"]["jra"]["failed"] == 1
    assert summary["verificationByCircuit"]["nar"]["verified"] == 1


def test_ci_exit_rejects_inconsistent_counts_even_if_report_claims_verified():
    result = {"allIndexedSavedOriginalsVerified": True}
    assert audit_exit_code(result, {"verificationCountsReconciled": False}) == 1
    assert audit_exit_code(result, {"verificationCountsReconciled": True}) == 0
    assert audit_exit_code(
        {"allIndexedSavedOriginalsVerified": False},
        {"verificationCountsReconciled": True},
    ) == 1
