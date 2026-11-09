#!/usr/bin/env python3
"""Score previously frozen production masterAnalysis against final results.

Usage:
  python scripts/arvexq_master_scoreboard.py exported_race_details.json [out.json]

Input: JSON list of full race details, or {"races":[...]}, or one full
detail. Each item may be wrapped as {"detail": {...}}. No web fetching,
result backfill or score refitting is performed here.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.master_scoreboard import grade_master_pairs  # noqa: E402
from rewrite.analysis.master_selection import select_daily_races  # noqa: E402


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    payload = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("races"), list):
        records = payload["races"]
    elif isinstance(payload, dict):
        records = [payload]
    else:
        raise ValueError("expected race details JSON object or list")
    details = []
    for item in records:
        if not isinstance(item, dict):
            continue
        detail = item.get("detail") if isinstance(item.get("detail"), dict) else item
        details.append(detail)
    report = grade_master_pairs(details)
    by_date = defaultdict(list)
    for detail in details:
        if detail.get("date"):
            by_date[detail["date"]].append({
                "raceId": detail.get("id") or detail.get("raceId"),
                "masterAnalysis": detail.get("masterAnalysis") or {},
            })
    report["shadowSelectionByDate"] = {
        date: select_daily_races(items) for date, items in sorted(by_date.items())
    }
    body = json.dumps(report, indent=2, ensure_ascii=False)
    print(body)
    if len(argv) == 2:
        Path(argv[1]).write_text(body + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
