#!/usr/bin/env python3
"""Read-only exhaustive integrity scan of existing saved evidence, no HTTP."""
from __future__ import annotations
import argparse
from collections import Counter
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
    condensed["errorCodes"]=dict(sorted(Counter(
        error.get("code", "unknown") for error in result["errors"]).items()))
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
    return 0 if result["allIndexedSavedOriginalsVerified"] else 1


if __name__=="__main__":
    raise SystemExit(main())
