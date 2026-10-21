#!/usr/bin/env python3
"""Offline-only validation of genuine pre-off captures against separate results.

Never downloads races or constructs after-the-fact pre-off snapshots.
No automatic promotion to public forecast, marks, or tickets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arvexq.components.item_125.preoff_evidence_store import open_store


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True,
                        help="Existing append-only local research SQLite database")
    parser.add_argument("--results", type=Path, required=True,
                        help="Independent finalized race-result list (JSON)")
    parser.add_argument("--report", type=Path,
                        help="Optional local research report output (JSON)")
    args = parser.parse_args(argv)
    if not args.store.is_file():
        parser.error("existing archived pre-off evidence database required")
    data = json.loads(args.results.read_text(encoding="utf-8"))
    # The optional, retired research evaluator is checked only for an actual run.
    # --help must remain usable; no evidence store is opened before this guard.
    try:
        from arvexq.forecast.verified_holdout import evaluate_verified_circuits
    except ModuleNotFoundError as exc:
        if exc.name != "arvexq.forecast.verified_holdout":
            raise
        parser.error(
            "verified holdout evaluator unavailable (retired research module); "
            "no capture database opened or modified"
        )
    with open_store(args.store) as conn:
        report = evaluate_verified_circuits(conn, data)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report:
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
