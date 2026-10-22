#!/usr/bin/env python3
"""Verify that D1 actually contains the observed inputs before any AI prediction.

Read-only stage; no parallel acquisition provider, guesses, or database writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.components.item_111.persisted_inputs import verify_persisted_facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--saved", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    saved = json.loads(Path(args.saved).read_text(encoding="utf-8"))
    issues = verify_persisted_facts(source, saved)
    expected = len(source.get("summaries") or [])
    found = len(saved.get("races") or [])
    data = {"expected": expected, "stored": found, "errors": issues,
            "verified": bool(expected and not issues)}
    Path(args.report).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("D1_PERSISTED_FACTS", "expected=",expected,"saved=",found,"errors=",len(issues))
    for issue in issues[:25]:
        print("D1_PERSISTED_FACTS_MISMATCH", issue)
    return 0 if data["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
