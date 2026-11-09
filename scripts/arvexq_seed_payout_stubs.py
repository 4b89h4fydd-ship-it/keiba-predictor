#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed stub details in a result-repair bundle from an archived card file.

One-off companion to the JRA payout history repair: a handful of stored
2026-10-31 JRA details are summary-only stubs (no horse column), so the
result-repair lane's base seeding silently drops them and their broken
payout combinations can never be re-fetched. This step replaces ONLY
bundle details that (a) carry no horses and (b) have an entry in the
seed file, with the archived pre-race detail captured by the rewrite
ingest (raw_snapshots api_race_detail). Nothing else in the bundle is
touched; races whose stored detail already has a card are left alone,
so the step is idempotent and safe to re-run.

Usage:
  arvexq_seed_payout_stubs.py --bundle bundle-jra.json \
      --seeds arvexq/payout_repair_requests/seeds-2026-10-31.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--seeds", required=True)
    args = parser.parse_args()

    bundle = _read_json(args.bundle)
    seed_doc = _read_json(args.seeds)
    seeds: dict[str, Any] = seed_doc.get("seeds") or {}
    if not seeds:
        print("::error::seed file carries no seeds")
        return 1

    details = bundle.get("details") or []
    replaced: list[str] = []
    replaced_stubs: dict[str, Any] = {}
    seen: set[str] = set()
    for idx, detail in enumerate(details):
        if not isinstance(detail, dict):
            continue
        rid = str(detail.get("id") or "")
        if detail.get("horses"):
            continue  # stored detail already has a card; never overwrite
        seed = seeds.get(rid)
        if seed is None:
            continue
        if str(seed.get("id") or "") != rid or not seed.get("horses"):
            print(f"::error::seed for {rid} is unusable (id/horses mismatch)")
            return 1
        # Keep the pristine pre-seed stub: for a nightly-compact
        # tombstone the repair payload must be shaped back to this
        # stub plus the refreshed result fields (the protect layer
        # admits only a result-only write over a tombstone). The
        # repair step reads the sidecar and applies the protect
        # predicate itself before shaping anything.
        replaced_stubs[rid] = detail
        details[idx] = seed
        replaced.append(rid)
        seen.add(rid)

    missing = sorted(set(seeds) - seen)
    if missing:
        print(f"::error::seed targets not present as stubs in bundle: {missing}")
        return 1

    bundle["details"] = details
    Path(args.bundle).write_text(
        json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    sidecar = Path(str(args.bundle) + ".tombstone-stubs.json")
    sidecar.write_text(
        json.dumps({"stubs": replaced_stubs}, ensure_ascii=False),
        encoding="utf-8")
    print(f"seeded {len(replaced)} stub details: {sorted(replaced)}")
    print(f"recorded {len(replaced_stubs)} pre-seed stubs in {sidecar.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
