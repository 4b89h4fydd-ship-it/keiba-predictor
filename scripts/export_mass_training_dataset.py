#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.mass_training_store import load_frozen_training_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export leakage-safe ARVEXQ mass-feature training rows")
    parser.add_argument("db", help="Path to RaceDataBank sqlite file")
    parser.add_argument("output", help="Output JSONL path")
    parser.add_argument("--circuit", default="")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    args = parser.parse_args()

    rows = load_frozen_training_rows(
        args.db,
        circuit=args.circuit,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    races = len({str(row.get("raceId") or "") for row in rows})
    features = len({k for row in rows for k in (row.get("features") or {})})
    print(json.dumps({"rows": len(rows), "races": races, "features": features, "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
