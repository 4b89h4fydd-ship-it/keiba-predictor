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
    condensed["errorCount"]=len(result["errors"])
    condensed["verificationByCircuit"] = {
        circuit: {"expected": counts.get("expected"),
                  "verified": counts.get("verified"),
                  "failed": counts.get("failed")}
        for circuit, counts in sorted(result["circuits"].items())
    }
    def valid_count(value):
        return type(value) is int and value >= 0

    condensed["circuitCountReconciliation"] = {
        circuit: (all(valid_count(value) for value in counts.values())
                  and counts["expected"] == counts["verified"] + counts["failed"])
        for circuit, counts in condensed["verificationByCircuit"].items()
    }
    condensed["circuitKeysValid"] = set(condensed["verificationByCircuit"]) == {"jra", "nar"}
    condensed["verificationCountsReconciled"] = (
        condensed["circuitKeysValid"]
        and all(condensed["circuitCountReconciliation"].values())
        and valid_count(result["expectedRacecards"])
        and valid_count(result["hashVerifiedRacecards"])
        and sum(v["expected"] for v in condensed["verificationByCircuit"].values()) == result["expectedRacecards"]
        and sum(v["verified"] for v in condensed["verificationByCircuit"].values()) == result["hashVerifiedRacecards"]
    )
    condensed["errorCodes"]=dict(sorted(Counter(
        error.get("code", "unknown") for error in result["errors"]).items()))
    dates = result.get("verifiedSavedDates")
    date_range = result.get("dateRange")
    count = result.get("dateCount")
    try:
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
    condensed["savedDateSelectionReconciled"] = dates_valid
    condensed["verifiedSavedDates"] = dates
    condensed["integrityScanRange"]=result["integrityScanRange"]
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
    return 0 if (result["allIndexedSavedOriginalsVerified"]
                 and condensed["verificationCountsReconciled"]
                 and condensed["savedDateSelectionReconciled"]) else 1


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--archive-dir", type=Path, default=ROOT/"arvexq"/"ui"/"static")
    p.add_argument("--out", type=Path, default=Path("arvexq-v3-full-archive-audit.json"))
    a=p.parse_args()
    result=verify_saved_week(a.archive_dir, days=a.days)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    condensed=summarize_for_ci(result)
    print("ARVEXQ_V3_FULL_ARCHIVE_AUDIT_JSON="+json.dumps(condensed,ensure_ascii=False))
    return audit_exit_code(result, condensed)


if __name__=="__main__":
    raise SystemExit(main())
