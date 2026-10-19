#!/usr/bin/env python3
"""Read-only exhaustive integrity scan of existing saved evidence, no HTTP."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from arvexq.v3.audit.full_archive import verify_saved_week


def summarize_for_ci(result):
    """Small, deterministic, read-only audit evidence for Actions logs."""
    condensed={k:result[k] for k in ("dateRange","expectedRacecards","hashVerifiedRacecards",
                 "allIndexedSavedOriginalsVerified","circuits")}
    errors = result.get("errors")
    error_rows = errors if type(errors) is list else []
    condensed["errorCount"] = len(error_rows)
    circuits = result.get("circuits")
    circuit_rows = circuits if type(circuits) is dict else {}
    condensed["verificationByCircuit"] = {
        circuit: {"expected": counts.get("expected"),
                  "verified": counts.get("verified"),
                  "failed": counts.get("failed")}
        for circuit, counts in circuit_rows.items()
        if type(circuit) is str and type(counts) is dict
    }
    def valid_count(value):
        return type(value) is int and value >= 0

    condensed["circuitCountReconciliation"] = {
        circuit: (all(valid_count(value) for value in counts.values())
                  and counts["expected"] == counts["verified"] + counts["failed"])
        for circuit, counts in condensed["verificationByCircuit"].items()
    }
    condensed["circuitKeysValid"] = (type(circuits) is dict
                                     and set(circuits) == {"jra", "nar"}
                                     and len(condensed["verificationByCircuit"]) == 2)
    condensed["verificationCountsReconciled"] = (
        condensed["circuitKeysValid"]
        and all(condensed["circuitCountReconciliation"].values())
        and valid_count(result["expectedRacecards"])
        and valid_count(result["hashVerifiedRacecards"])
        and sum(v["expected"] for v in condensed["verificationByCircuit"].values()) == result["expectedRacecards"]
        and sum(v["verified"] for v in condensed["verificationByCircuit"].values()) == result["hashVerifiedRacecards"]
    )
    # Normalize malformed codes before counting; mixed types cannot be sorted.
    error_codes = [
        error["code"] if (type(error) is dict and
                          type(error.get("code")) is str and error["code"])
        else "malformed-error-record"
        for error in error_rows
    ]
    condensed["verificationSuccessReconciled"] = (
        condensed["verificationCountsReconciled"]
        and result["expectedRacecards"] > 0
        and result["hashVerifiedRacecards"] == result["expectedRacecards"]
        and all(row["failed"] == 0 for row in condensed["verificationByCircuit"].values())
    )
    condensed["errorCodes"] = dict(sorted(Counter(error_codes).items()))
    condensed["errorSummaryReconciled"] = (
        type(errors) is list
        and all(type(error) is dict and type(error.get("code")) is str
                and bool(error["code"]) for error in error_rows)
        and sum(condensed["errorCodes"].values()) == condensed["errorCount"]
    )
    dates = result.get("verifiedSavedDates")
    date_range = result.get("dateRange")
    count = result.get("dateCount")
    try:
        if type(dates) is not list or any(type(d) is not str for d in dates):
            raise ValueError("saved dates must be a list of strings")
        parsed = [date.fromisoformat(d) for d in dates]
        dates_valid = (type(count) is int and count > 0
                       and type(dates) is list and len(dates) == count
                       and all(type(d) is str and p.isoformat() == d
                               for d, p in zip(dates, parsed))
                       and parsed == sorted(set(parsed))
                       and type(date_range) is list and len(date_range) == 2
                       and date_range == [dates[0], dates[-1]]
                       and result.get("pairedDateRangeMatchesSelection") is True)
    except (TypeError, ValueError, IndexError):
        dates_valid = False
    requested_end = result.get("requestedEndDate")
    try:
        cutoff_valid = (requested_end is None or
                        (type(requested_end) is str
                         and date.fromisoformat(requested_end).isoformat() == requested_end
                         and dates_valid
                         and parsed[-1] <= date.fromisoformat(requested_end)))
    except (ValueError, TypeError):
        cutoff_valid = False
    condensed["requestedEndDateReconciled"] = cutoff_valid
    condensed["requestedEndDate"] = requested_end
    condensed["savedDateSelectionReconciled"] = dates_valid
    condensed["verifiedSavedDates"] = dates
    scan_range = result.get("integrityScanRange")
    unpaired = result.get("unpairedSavedDays")
    try:
        if type(scan_range) is not list or any(type(d) is not str for d in scan_range):
            raise ValueError("scan dates must be a list of strings")
        scan_dates = [date.fromisoformat(d) for d in scan_range]
        scan_valid = (type(scan_range) is list and len(scan_range) == 2
                      and all(type(d) is str and p.isoformat() == d
                              for d, p in zip(scan_range, scan_dates))
                      and scan_dates[0] <= scan_dates[1]
                      and dates_valid and scan_dates[0] == parsed[0]
                      and scan_dates[1] >= parsed[-1]
                      and (requested_end is None or
                           scan_dates[1] <= date.fromisoformat(requested_end))
                      and type(result.get("integrityScanCalendarDays")) is int
                      and result["integrityScanCalendarDays"] == (scan_dates[1] - scan_dates[0]).days + 1
                      and type(unpaired) is list
                      and len({row.get("date") for row in unpaired if type(row) is dict}) == len(unpaired)
                      and all(type(row) is dict
                              and row.get("filePresence") in ("racecard-only", "manifest-only")
                              and type(row.get("date")) is str
                              and scan_dates[0] <= date.fromisoformat(row["date"]) <= scan_dates[1]
                              and date.fromisoformat(row["date"]).isoformat() == row["date"]
                              for row in unpaired))
    except (TypeError, ValueError, IndexError, KeyError):
        scan_valid = False
    # Every one-sided day in the scan must have a corresponding integrity error.
    unpaired_error_days = sorted(
        (e.get("date"), e.get("filePresence"))
        for e in error_rows
        if type(e) is dict and e.get("code") == "unpaired-saved-day"
        and type(e.get("date")) is str and type(e.get("filePresence")) is str
    )
    unpaired_report_days = sorted(
        (row.get("date"), row.get("filePresence"))
        for row in unpaired
        if type(row) is dict and type(row.get("date")) is str
        and type(row.get("filePresence")) is str
    ) if type(unpaired) is list else []
    condensed["unpairedErrorsReconciled"] = (
        type(unpaired) is list
        and len(unpaired_report_days) == len(unpaired)
        and unpaired_error_days == unpaired_report_days
    )
    condensed["integrityScanRangeReconciled"] = scan_valid
    condensed["integrityScanRange"]=scan_range
    condensed["unpairedSavedDays"]=result["unpairedSavedDays"]
    triage = result["runnerEvidenceTriage"]
    condensed["runnerEvidenceTriage"] = {
        "zeroObservedPriorRuns": triage["zeroObservedPriorRuns"],
        "byCircuitCategory": triage["byCircuitCategory"],
        "missingCardCarriedWeight": triage["missingCardCarriedWeight"],
        "missingWeightByState": triage["missingWeightByState"],
    }
    return condensed


def audit_exit_code(result, condensed):
    return 0 if (result.get("allIndexedSavedOriginalsVerified") is True
                 and condensed.get("errorCount") == 0
                 and condensed.get("errorCodes") == {}
                 and condensed.get("verificationCountsReconciled") is True
                 and condensed.get("verificationSuccessReconciled") is True
                 and condensed.get("savedDateSelectionReconciled") is True
                 and condensed.get("requestedEndDateReconciled") is True
                 and condensed.get("integrityScanRangeReconciled") is True
                 and condensed.get("unpairedErrorsReconciled") is True
                 and condensed.get("errorSummaryReconciled") is True) else 1


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--archive-dir", type=Path, default=ROOT/"arvexq"/"ui"/"static")
    p.add_argument("--end-date", type=str, default=None,
                   help="Inclusive YYYY-MM-DD cutoff for reproducible historical audits")
    p.add_argument("--out", type=Path, default=Path("arvexq-v3-full-archive-audit.json"))
    a=p.parse_args()
    result=verify_saved_week(a.archive_dir, days=a.days, end_date=a.end_date)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    condensed=summarize_for_ci(result)
    print("ARVEXQ_V3_FULL_ARCHIVE_AUDIT_JSON="+json.dumps(condensed,ensure_ascii=False))
    return audit_exit_code(result, condensed)


if __name__=="__main__":
    raise SystemExit(main())
