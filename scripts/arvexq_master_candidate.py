#!/usr/bin/env python3
"""Run the 18-section master *shadow* candidate against a saved API race.

Usage:
  python scripts/arvexq_master_candidate.py snapshot.json [output.json]

snapshot.json: {"summary": <production /api/day race row>,
                "detail": <production /api/race detail>}
This command never writes to D1 or alters frozen production forecasts.
It only processes stored pre-off facts; use pre-off snapshots for backtests.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.master_v1 import forecast_master  # noqa: E402
from rewrite.data.normalize import normalize_race  # noqa: E402


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("snapshot must be an object")
    summary, detail = payload.get("summary"), payload.get("detail")
    if not isinstance(summary, dict) or not isinstance(detail, dict):
        raise ValueError("snapshot requires summary and detail objects")
    if detail.get("result") and isinstance(detail["result"], dict):
        if detail["result"].get("finishers") or detail["result"].get("payouts"):
            raise ValueError("result-bearing snapshots are forbidden; pre-off only")
    race = normalize_race(summary, detail, "saved-preoff-snapshot")
    report = forecast_master(race)
    body = json.dumps(report, ensure_ascii=False, indent=2)
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(body + "\n", encoding="utf-8")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
