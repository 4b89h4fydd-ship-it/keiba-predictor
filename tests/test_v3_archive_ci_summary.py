"""Stage 39: ensure CI summary describes failures without claiming official coverage."""
from scripts.arvexq_v3_full_archive_audit import summarize_for_ci, audit_exit_code


def test_ci_summary_aggregates_error_codes_and_unpaired_days():
    result = {
        "dateRange": ["2026-10-12", "2026-10-14"],
        "integrityScanRange": ["2026-10-12", "2026-10-15"],
        "integrityScanCalendarDays": 4,
        "expectedRacecards": 2,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": False,
        "circuits": {"jra": {"expected": 0, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
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
    assert summary["errorSummaryReconciled"] is True
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
        "integrityScanCalendarDays": 1,
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
    assert audit_exit_code(result, {"verificationCountsReconciled": True, "verificationSuccessReconciled": True, "savedDateSelectionReconciled": True, "integrityScanRangeReconciled": True, "requestedEndDateReconciled": True, "unpairedErrorsReconciled": True, "errorSummaryReconciled": True, "errorCount": 0, "errorCodes": {}}) == 0
    assert audit_exit_code(result, {"verificationCountsReconciled": True, "savedDateSelectionReconciled": True, "integrityScanRangeReconciled": True}) == 1
    assert audit_exit_code(
        {"allIndexedSavedOriginalsVerified": False},
        {"verificationCountsReconciled": True},
    ) == 1


def test_ci_summary_rejects_missing_circuit_and_invalid_counts():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "errors": [], "unpairedSavedDays": [],
        "runnerEvidenceTriage": {
            "zeroObservedPriorRuns": 0, "byCircuitCategory": {},
            "missingCardCarriedWeight": 0, "missingWeightByState": {},
        },
    }
    for circuits in (
        {"jra": {"expected": 1, "verified": 1, "failed": 0}},
        {"jra": {"expected": True, "verified": 1, "failed": 0},
         "nar": {"expected": 0, "verified": 0, "failed": 0}},
        {"jra": {"expected": 1, "verified": 1, "failed": 0},
         "nar": {"expected": -1, "verified": -1, "failed": 0}},
        {"jra": {"expected": "1", "verified": 1, "failed": 0},
         "nar": {"expected": 0, "verified": 0, "failed": 0}},
        {"jra": {"expected": 1, "verified": None, "failed": 0},
         "nar": {"expected": 0, "verified": 0, "failed": 0}},
        {"jra": {"expected": 1, "verified": 1},
         "nar": {"expected": 0, "verified": 0, "failed": 0}},
        {"jra": {"expected": 1, "failed": 0},
         "nar": {"expected": 0, "verified": 0, "failed": 0}},
    ):
        summary = summarize_for_ci({**base, "circuits": circuits})
        assert summary["verificationCountsReconciled"] is False
        assert audit_exit_code(base, summary) == 1


def test_ci_saved_date_selection_rejects_duplicates_and_mismatched_range():
    base = {
        "dateRange": ["2026-10-12", "2026-10-14"],
        "dateCount": 2,
        "verifiedSavedDates": ["2026-10-12", "2026-10-14"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-14"],
        "integrityScanCalendarDays": 3,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [], "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    good = summarize_for_ci(base)
    assert good["savedDateSelectionReconciled"] is True
    assert good["requestedEndDateReconciled"] is True
    assert good["integrityScanRangeReconciled"] is True
    assert audit_exit_code(base, good) == 0
    for overrides in (
        {"dateCount": 3},
        {"verifiedSavedDates": ["2026-10-12", "2026-10-12"]},
        {"dateRange": ["2026-10-12", "2026-10-15"]},
        {"verifiedSavedDates": ["2026-10-14", "2026-10-12"]},
        {"verifiedSavedDates": ["2026-10-12", "invalid"]},
        {"pairedDateRangeMatchesSelection": False},
    ):
        broken = {**base, **overrides}
        summary = summarize_for_ci(broken)
        assert summary["savedDateSelectionReconciled"] is False
        assert audit_exit_code(broken, summary) == 1


def test_ci_rejects_invalid_integrity_scan_bounds_and_unpaired_dates():
    base = {
        "dateRange": ["2026-10-12", "2026-10-14"],
        "dateCount": 2,
        "verifiedSavedDates": ["2026-10-12", "2026-10-14"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-15"],
        "integrityScanCalendarDays": 4,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [],
        "unpairedSavedDays": [{"date": "2026-10-15", "filePresence": "manifest-only"}],
        "runnerEvidenceTriage": {
            "zeroObservedPriorRuns": 0, "byCircuitCategory": {},
            "missingCardCarriedWeight": 0, "missingWeightByState": {},
        },
    }
    assert summarize_for_ci(base)["integrityScanRangeReconciled"] is True
    for overrides in (
        {"integrityScanRange": ["2026-10-13", "2026-10-15"]},
        {"integrityScanRange": ["2026-10-12", "2026-10-13"]},
        {"integrityScanRange": ["2026-10-15", "2026-10-12"]},
        {"integrityScanRange": ["bad", "2026-10-15"]},
        {"unpairedSavedDays": [{"date": "2026-10-16", "filePresence": "manifest-only"}]},
        {"unpairedSavedDays": [{"date": "2026-10-15", "filePresence": "both-present"}]},
        {"integrityScanCalendarDays": 3},
        {"unpairedSavedDays": [{"date": "2026-10-15", "filePresence": "manifest-only"},
                               {"date": "2026-10-15", "filePresence": "manifest-only"}]},
    ):
        broken = {**base, **overrides}
        summary = summarize_for_ci(broken)
        assert summary["integrityScanRangeReconciled"] is False
        assert audit_exit_code(broken, summary) == 1


def test_ci_rejects_missing_or_empty_error_codes():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    good = summarize_for_ci({**base, "errors": []})
    assert good["errorSummaryReconciled"] is True
    assert audit_exit_code(base, good) == 0
    for bad_errors in ([{}], [{"code": ""}], [{"code": None}]):
        summary = summarize_for_ci({**base, "errors": bad_errors})
        assert summary["errorSummaryReconciled"] is False
        assert audit_exit_code(base, summary) == 1


def test_ci_exit_rejects_errors_even_if_success_flag_is_true():
    result = {"allIndexedSavedOriginalsVerified": True}
    flags = {"verificationCountsReconciled": True,
             "verificationSuccessReconciled": True,
             "savedDateSelectionReconciled": True,
             "integrityScanRangeReconciled": True,
             "requestedEndDateReconciled": True,
             "unpairedErrorsReconciled": True,
             "errorSummaryReconciled": True,
             "errorCount": 0, "errorCodes": {}}
    assert audit_exit_code(result, flags) == 0
    assert audit_exit_code(result, {**flags, "errorCount": 1,
                                   "errorCodes": {"invalid-snapshot": 1}}) == 1
    assert audit_exit_code(result, {**flags, "errorCodes": {"invalid-snapshot": 1}}) == 1
    assert audit_exit_code(result, {**flags, "errorCount": None}) == 1


def test_cli_passes_explicit_end_date_to_archive_verifier(monkeypatch, tmp_path):
    import sys
    import scripts.arvexq_v3_full_archive_audit as cli

    received = {}
    def fake_verify(archive_dir, *, days, end_date):
        received.update(archive_dir=archive_dir, days=days, end_date=end_date)
        return {"allIndexedSavedOriginalsVerified": False}

    monkeypatch.setattr(cli, "verify_saved_week", fake_verify)
    monkeypatch.setattr(cli, "summarize_for_ci", lambda result: {
        "verificationCountsReconciled": False,
        "savedDateSelectionReconciled": False,
        "integrityScanRangeReconciled": False,
        "errorSummaryReconciled": False,
        "errorCount": 1,
        "errorCodes": {"missing-original": 1},
    })
    output = tmp_path / "audit.json"
    monkeypatch.setattr(sys, "argv", ["audit", "--days", "3", "--end-date",
                                      "2026-10-14", "--archive-dir", str(tmp_path),
                                      "--out", str(output)])
    assert cli.main() == 1
    assert received == {"archive_dir": tmp_path, "days": 3, "end_date": "2026-10-14"}
    assert output.is_file()


def test_ci_rejects_requested_cutoff_before_selected_saved_dates():
    base = {
        "dateRange": ["2026-10-12", "2026-10-14"],
        "dateCount": 2,
        "verifiedSavedDates": ["2026-10-12", "2026-10-14"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-14"],
        "integrityScanCalendarDays": 3,
        "expectedRacecards": 1, "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [], "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    assert summarize_for_ci({**base, "requestedEndDate": "2026-10-14"})["requestedEndDateReconciled"] is True
    assert summarize_for_ci({**base, "requestedEndDate": None})["requestedEndDateReconciled"] is True
    for bad in ("2026-10-13", "20261014", "2026-99-99", True):
        report = summarize_for_ci({**base, "requestedEndDate": bad})
        assert report["requestedEndDateReconciled"] is False
        assert audit_exit_code(base, report) == 1


def test_ci_rejects_integrity_scan_past_requested_cutoff():
    base = {
        "dateRange": ["2026-10-12", "2026-10-14"],
        "dateCount": 2,
        "verifiedSavedDates": ["2026-10-12", "2026-10-14"],
        "pairedDateRangeMatchesSelection": True,
        "requestedEndDate": "2026-10-14",
        "integrityScanRange": ["2026-10-12", "2026-10-14"],
        "integrityScanCalendarDays": 3,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [],
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    good = summarize_for_ci(base)
    assert good["integrityScanRangeReconciled"] is True
    assert audit_exit_code(base, good) == 0
    beyond = {**base, "integrityScanRange": ["2026-10-12", "2026-10-15"],
              "integrityScanCalendarDays": 4}
    bad = summarize_for_ci(beyond)
    assert bad["requestedEndDateReconciled"] is True
    assert bad["integrityScanRangeReconciled"] is False
    assert audit_exit_code(beyond, bad) == 1


def test_ci_requires_unpaired_dates_to_match_integrity_errors():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-13"],
        "integrityScanCalendarDays": 2,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [{"date": "2026-10-13", "code": "unpaired-saved-day",
                    "filePresence": "manifest-only"}],
        "unpairedSavedDays": [{"date": "2026-10-13", "filePresence": "manifest-only"}],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    assert summarize_for_ci(base)["unpairedErrorsReconciled"] is True
    for changed in (
        {"errors": []},
        {"errors": [{"date": "2026-10-13", "code": "unpaired-saved-day",
                     "filePresence": "racecard-only"}]},
        {"errors": base["errors"] + base["errors"]},
        {"unpairedSavedDays": []},
    ):
        report = summarize_for_ci({**base, **changed})
        assert report["unpairedErrorsReconciled"] is False
        assert audit_exit_code(base, report) == 1


def test_ci_handles_malformed_error_collections_without_exceptions():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    for malformed in (None, "bad", {"code": "bad"}, [None], ["bad"], [12]):
        summary = summarize_for_ci({**base, "errors": malformed})
        assert summary["errorSummaryReconciled"] is False
        assert audit_exit_code(base, summary) == 1


def test_ci_rejects_malformed_circuit_collections_without_exceptions():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "errors": [],
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    for malformed in (None, [], "bad", {"jra": None, "nar": {}},
                      {"jra": [], "nar": {"expected": 0, "verified": 0, "failed": 0}}):
        summary = summarize_for_ci({**base, "circuits": malformed})
        assert summary["circuitKeysValid"] is False
        assert summary["verificationCountsReconciled"] is False
        assert audit_exit_code(base, summary) == 1


def test_ci_rejects_mixed_type_circuit_keys_without_sort_crash():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1,
        "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "errors": [],
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    for circuits in ({1: {"expected": 1, "verified": 1, "failed": 0},
                      "nar": {"expected": 0, "verified": 0, "failed": 0}},
                     {"jra": {"expected": 1, "verified": 1, "failed": 0},
                      "nar": {"expected": 0, "verified": 0, "failed": 0},
                      None: {}}):
        summary = summarize_for_ci({**base, "circuits": circuits})
        assert summary["circuitKeysValid"] is False
        assert summary["verificationCountsReconciled"] is False
        assert audit_exit_code(base, summary) == 1


def test_ci_rejects_malformed_error_code_types_without_sort_crash():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1, "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1, "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    for bad_code in (None, 7, True, ["bad"], {"x": 1}):
        summary = summarize_for_ci({**base, "errors": [
            {"code": "known-error"}, {"code": bad_code},
        ]})
        assert summary["errorCodes"] == {"known-error": 1, "malformed-error-record": 1}
        assert summary["errorSummaryReconciled"] is False
        assert audit_exit_code(base, summary) == 1


def test_ci_rejects_non_string_selected_and_scan_dates_without_exceptions():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 1, "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [], "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    for updates in (
        {"verifiedSavedDates": [20261012]},
        {"verifiedSavedDates": [None]},
        {"verifiedSavedDates": "2026-10-12"},
        {"integrityScanRange": [20261012, "2026-10-12"]},
        {"integrityScanRange": {"start": "2026-10-12"}},
    ):
        report = summarize_for_ci({**base, **updates})
        assert (report["savedDateSelectionReconciled"] is False
                or report["integrityScanRangeReconciled"] is False)
        assert audit_exit_code(base, report) == 1


def test_ci_rejects_mixed_type_unpaired_records_without_sort_crash():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1, "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-13"],
        "integrityScanCalendarDays": 2,
        "expectedRacecards": 1, "hashVerifiedRacecards": 1,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 1, "verified": 1, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [], "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    for bad in (
        {"date": 20261013, "filePresence": "manifest-only"},
        {"date": "2026-10-13", "filePresence": None},
        {"date": ["2026-10-13"], "filePresence": "manifest-only"},
        None,
    ):
        report = summarize_for_ci({**base, "unpairedSavedDays": [bad]})
        assert report["integrityScanRangeReconciled"] is False
        assert report["unpairedErrorsReconciled"] is False
        assert audit_exit_code(base, report) == 1


def test_ci_verification_success_requires_nonempty_all_verified_and_no_failures():
    base = {
        "dateRange": ["2026-10-12", "2026-10-12"],
        "dateCount": 1,
        "verifiedSavedDates": ["2026-10-12"],
        "pairedDateRangeMatchesSelection": True,
        "integrityScanRange": ["2026-10-12", "2026-10-12"],
        "integrityScanCalendarDays": 1,
        "expectedRacecards": 2, "hashVerifiedRacecards": 2,
        "allIndexedSavedOriginalsVerified": True,
        "circuits": {"jra": {"expected": 2, "verified": 2, "failed": 0},
                     "nar": {"expected": 0, "verified": 0, "failed": 0}},
        "errors": [], "unpairedSavedDays": [],
        "runnerEvidenceTriage": {"zeroObservedPriorRuns": 0, "byCircuitCategory": {},
                                 "missingCardCarriedWeight": 0, "missingWeightByState": {}},
    }
    good = summarize_for_ci(base)
    assert good["verificationSuccessReconciled"] is True
    assert audit_exit_code(base, good) == 0
    for updates in (
        {"expectedRacecards": 0, "hashVerifiedRacecards": 0,
         "circuits": {"jra": {"expected": 0, "verified": 0, "failed": 0},
                      "nar": {"expected": 0, "verified": 0, "failed": 0}}},
        {"hashVerifiedRacecards": 1,
         "circuits": {"jra": {"expected": 2, "verified": 1, "failed": 1},
                      "nar": {"expected": 0, "verified": 0, "failed": 0}}},
    ):
        broken = {**base, **updates}
        summary = summarize_for_ci(broken)
        assert summary["verificationSuccessReconciled"] is False
        assert audit_exit_code(broken, summary) == 1
