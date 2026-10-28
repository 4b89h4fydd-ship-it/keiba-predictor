#!/usr/bin/env python3
"""Ingest one day of races into the rewrite data store.

Reads the production API (read-only), stores byte-exact raw snapshots,
normalizes every race and prints a field-level quality report. Races
whose detail cannot be fetched are reported, never fabricated.

Usage: python scripts/arvexq_rewrite_ingest.py YYYY-MM-DD [db_path]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.data.normalize import normalize_race  # noqa: E402
from rewrite.data.quality import day_quality  # noqa: E402
from rewrite.data.sources import (  # noqa: E402
    SourceUnavailable,
    fetch_api_race_detail,
    fetch_api_races,
)
from rewrite.data.store import Store  # noqa: E402


def ingest(date: str, store: Store) -> dict:
    listing = fetch_api_races(date)
    listing_sha, _ = store.save_raw(listing, race_key=f"date:{date}")
    summaries = listing.json().get("races") or []
    races = []
    failures: list[dict] = []
    existing = {
        row[0]
        for row in store.db.execute("SELECT race_id FROM normalized_races")
    }
    excluded: list[dict] = []
    for summary in summaries:
        race_id = str(summary.get("race_id") or summary.get("id") or "")
        if str(summary.get("track") or "").strip() in {"帯広", "帯広ば", "帯広ばんえい"}:
            excluded.append({"race_id": race_id, "reason": "banei-excluded"})
            continue  # excluded venue: never fetched, never a failure
        if race_id in existing:
            continue  # resume support: never refetch stored races
        try:
            detail_payload = fetch_api_race_detail(race_id)
        except SourceUnavailable as exc:
            failures.append({"race_id": race_id, "error": str(exc)})
            continue
        detail_sha, _ = store.save_raw(detail_payload, race_key=race_id)
        detail = detail_payload.json().get("detail") or {}
        try:
            race = normalize_race(summary, detail, source=detail_payload.source_url)
        except ValueError as exc:  # e.g. banei exclusion
            failures.append({"race_id": race_id, "error": f"rejected: {exc}"})
            continue
        store.save_normalized(race, snapshot_sha256=detail_sha)
        races.append(race)
    if existing:
        races = store.load_races()  # resumed run: report over the full day
    report = day_quality(races)
    report["date"] = date
    report["listing_snapshot_sha256"] = listing_sha
    report["fetch_failures"] = failures
    report["excluded"] = excluded
    store.save_quality(date, report)
    return report


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    date = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else f"var/rewrite-{date}.sqlite3"
    store = Store(db_path)
    try:
        report = ingest(date, store)
    finally:
        store.close()
    summary = {k: v for k, v in report.items() if k != "per_race"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
