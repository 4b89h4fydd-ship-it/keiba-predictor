#!/usr/bin/env python3
"""Rebuild normalized_races in ingest DBs from their stored raw snapshots.

Usage:
  python scripts/arvexq_rewrite_renormalize.py <db> [<db> ...]

Raw snapshots are the evidence and are never touched. The normalized
tables are derived data: when the normalizer gains a field (e.g. past
-run race titles), this re-derives them in place from the stored raw
payloads so historical DBs match what a fresh ingest would produce.
Mirrors the ingest flow exactly (same summary/detail pairing, same
banei handling), minus any network access.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.data.normalize import normalize_race  # noqa: E402
from rewrite.data.store import Store  # noqa: E402

BANEI_TRACKS = {"帯広", "帯広ば", "帯広ばんえい"}


def renormalize(db_path: str) -> dict:
    store = Store(db_path)
    try:
        listing_row = store.db.execute(
            "SELECT body FROM raw_snapshots WHERE kind='api_races' LIMIT 1"
        ).fetchone()
        summaries = {}
        if listing_row:
            listing = json.loads(listing_row[0])
            for summary in listing.get("races") or []:
                race_id = str(summary.get("race_id") or summary.get("id") or "")
                if race_id:
                    summaries[race_id] = summary
        details = store.db.execute(
            "SELECT race_key, body, sha256, source_url FROM raw_snapshots "
            "WHERE kind='api_race_detail'"
        ).fetchall()
        races = []
        skipped = 0
        for race_key, body, sha, url in details:
            payload = json.loads(body)
            detail = payload.get("detail") or {}
            summary = summaries.get(race_key)
            if summary is None:
                skipped += 1
                continue
            if str(summary.get("track") or "").strip() in BANEI_TRACKS:
                skipped += 1
                continue
            try:
                race = normalize_race(summary, detail, source=url or "")
            except ValueError:
                skipped += 1
                continue
            races.append((race, sha))
        if not races:
            # Never wipe the derived table when the rebuild produced
            # nothing (e.g. a listing lookup mismatch). Raw snapshots
            # are intact; fix the cause and re-run.
            raise RuntimeError(
                f"{db_path}: rebuild produced 0 races; normalized table left untouched"
            )
        with store.db:
            store.db.execute("DELETE FROM normalized_races")
            for race, sha in races:
                store.save_normalized(race, snapshot_sha256=sha)
        return {"db": db_path, "races": len(races), "skipped": skipped}
    finally:
        store.close()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for db_path in sys.argv[1:]:
        print(json.dumps(renormalize(db_path), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
