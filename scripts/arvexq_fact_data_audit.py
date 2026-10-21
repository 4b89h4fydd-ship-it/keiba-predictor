#!/usr/bin/env python3
"""Read-only production fact audit; reports gaps without generating predictions."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.ingest.d1_day_readback import read_day
from arvexq.quality.fact_audit import audit_day


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.getenv("ARVEXQ_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev"))
    parser.add_argument("--days", type=int, default=int(os.getenv("ARVEXQ_DAYS", "7")))
    parser.add_argument("--end-date", default=os.getenv("ARVEXQ_END_DATE", ""))
    parser.add_argument("--report", default="fact-data-audit.json")
    parser.add_argument("--verify-display", action="store_true",
                        help="Compare persisted API facts with the PWA display API (read-only)")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("days must be positive")
    end = (datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else
           datetime.now(ZoneInfo("Asia/Tokyo")).date() - timedelta(days=1))
    days = []
    for offset in range(args.days - 1, -1, -1):
        day = (end - timedelta(days=offset)).isoformat()
        try:
            bundle = (read_day(args.api_base, day, verify_display=True) if args.verify_display
                      else read_day(args.api_base, day))
            days.append(audit_day(bundle))
        except Exception as exc:
            days.append({"date": day, "summaryRaces": None,
                         "readErrors": [{"error": type(exc).__name__ + ": " + str(exc)[:240]}],
                         "validationErrors": [], "allRaceReadsVerified": False})
    errors = sum(len(day["readErrors"]) + len(day["validationErrors"]) +
                 len(day.get("displayParityErrors") or []) for day in days)
    report = {"version": "arvexq-factual-data-audit-v2",
              "retrievedAt": datetime.now(timezone.utc).isoformat(),
              "start": days[0]["date"], "end": days[-1]["date"],
              "predictionLogicStatus": "予想ロジック仕様待ち", "errors": errors, "days": days}
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("ARVEXQ_FACT_DATA_AUDIT_JSON=" + json.dumps(report, ensure_ascii=False))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        lines = ["## ARVEXQ factual data audit", "", "Prediction calculation: 予想ロジック仕様待ち", "",
                 "| Date | Summaries | Read details | Horses | Read/validation/display errors |",
                 "|---|---:|---:|---:|---:|"]
        for day in days:
            observed = day.get("observed") or {}
            lines.append(f"| {day['date']} | {day['summaryRaces']} | {observed.get('races', 0)} | "
                         f"{observed.get('horses', 0)} | {len(day['readErrors'])+len(day['validationErrors'])+len(day.get('displayParityErrors') or [])} |")
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as output:
            output.write("\n".join(lines) + "\n")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
