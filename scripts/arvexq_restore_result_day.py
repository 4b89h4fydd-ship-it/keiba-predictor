#!/usr/bin/env python3
"""Medium result-stage entrypoint: retain D1 facts, restore only missing IDs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from arvexq.results.day_index import restore_if_empty


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()
    source = Path(args.bundle)
    value = json.loads(source.read_text(encoding="utf-8"))
    archive = ROOT / "arvexq/ui/static/racecards" / (args.date + ".json")
    result, method = restore_if_empty(value, args.date, archive)
    n = len(result.get("races") or [])
    Path(args.report).write_text(json.dumps(
        {"date": args.date, "races": n, "source": method},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print("RESULT_DAY_IDS", args.date, "races=", n, "source=", method)
    if n == 0:
        return 2
    if method != "d1":
        source.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
