"""Read-only CLI: audit genuine pre-off snapshot/receipt pairs, no predictions.

Input JSONL objects: {"snapshot": <frozen snapshot>, "receipt": <independent log receipt>}.
These records must already have been durably captured before off. Self-hashes do
not authenticate external storage timestamps; this CLI NEVER certifies that.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

from arvexq.rebuild.preoff_lanes import inspect_preoff


def audit(lines):
    seen = set()
    groups = defaultdict(lambda: {"acceptedRaces": 0, "dates": set(),
                                  "horsesWithAbilityEvidence": 0,
                                  "horsesWithStyleEvidence": 0,
                                  "horses": 0})
    failures = []
    count = 0
    for line_no, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        count += 1
        try:
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError("expected JSON object")
            report = inspect_preoff(obj.get("snapshot"), obj.get("receipt"))
            race_id = report["raceId"]
            if race_id in seen:
                raise ValueError("duplicate frozen race identity")
            seen.add(race_id)
            group = groups[report["modelFamily"]]
            group["acceptedRaces"] += 1
            group["dates"].add(report["raceDate"])
            group["horses"] += len(report["horseNumbers"])
            group["horsesWithAbilityEvidence"] += report["lanes"]["ability"]["horsesWithEvidence"]
            group["horsesWithStyleEvidence"] += report["lanes"]["running_style"]["horsesWithEvidence"]
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            failures.append({"line": line_no, "reason": str(exc)})
    summary = {family: {
        **{key: value for key, value in group.items() if key != "dates"},
        "distinctCaptureDates": len(group["dates"]),
        "modelTrainingApproved": False,
    } for family, group in sorted(groups.items())}
    return {
        "status": "research_evidence_audit_only",
        "externalTimestampVerification": "not_performed",
        "inputRecords": count, "acceptedRaces": len(seen),
        "rejectedRecords": len(failures),
        "jra": summary.get("jra-flat", {"acceptedRaces": 0, "modelTrainingApproved": False}),
        "nar": summary.get("nar-flat", {"acceptedRaces": 0, "modelTrainingApproved": False}),
        "rejects": failures,
        "probabilityCalibrationApproved": False,
        "marksAndTicketsEnabled": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", help="existing pre-off evidence JSONL, or - for stdin")
    args = parser.parse_args(argv)
    if args.jsonl == "-":
        result = audit(sys.stdin)
    else:
        with Path(args.jsonl).open(encoding="utf-8") as source:
            result = audit(source)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["inputRecords"] and result["rejectedRecords"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
