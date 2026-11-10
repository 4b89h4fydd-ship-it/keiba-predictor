#!/usr/bin/env python3
"""Read-only export of verified, sealed pre-off mass features from MotherDuck.

No result-derived feature reconstruction. Pre-off snapshots are restored with the
existing hash-checked decoder; settled results are joined only as training labels.
Never prints credentials or the archive payloads.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.mass_training_store import frozen_training_rows_from_detail

QUERY = """
SELECT race_id, CAST(snapshot_json AS VARCHAR) AS snapshot
FROM my_db.arvexq_analytics.race_snapshots
WHERE json_exists(snapshot_json, '$.massFeatureArchive')
  AND json_extract_string(snapshot_json, '$.result.status') = '確定'
  AND (CAST(? AS DATE) IS NULL OR race_date >= CAST(? AS DATE))
  AND (CAST(? AS DATE) IS NULL OR race_date <= CAST(? AS DATE))
ORDER BY race_date, race_id
"""


def transform_item(race_id: str, raw: str | dict) -> tuple[list[dict], str]:
    """Verify archived origin and produce labels only from settled results."""
    try:
        detail = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(detail, dict) or str(detail.get('id') or detail.get('raceId') or '') != str(race_id):
            return [], 'identity-mismatch'
        if '帯広' in race_id or str(detail.get('track') or '') == '帯広':
            return [], 'banei-excluded'
        archive = detail.get('massFeatureArchive')
        if not isinstance(archive, dict) or archive.get('originHashVerified') is not True or archive.get('originStatus') != 'verified':
            return [], 'unverified-archive'
        # The existing decoder rechecks the compressed SHA-256 and original
        # featureHash; a malformed archive is rejected, never backfilled.
        rows = frozen_training_rows_from_detail(detail)
        if not rows:
            return [], 'invalid-archive-or-result'
        expected = archive.get('horseCount')
        if expected is not None and len(rows) != int(expected):
            # Cancellation/DNF/partial result feeds must not silently shrink a
            # frozen ranking query. Exclude the entire race until reconciled.
            return [], 'incomplete-frozen-roster'
        if any(str(row.get('raceId') or '') != race_id for row in rows):
            return [], 'label-race-mismatch'
        return rows, 'exported'
    except (ValueError, TypeError, json.JSONDecodeError):
        return [], 'invalid-json'


def export(cursor, destination: Path) -> dict:
    """Stream a read-only query; retain no full dataset in memory."""
    counts = Counter()
    seen: set[str] = set()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', encoding='utf-8') as file:
        while True:
            batch = cursor.fetchmany(2)
            if not batch:
                break
            for race_id, raw in batch:
                rows, status = transform_item(str(race_id), raw)
                if status != 'exported':
                    counts[status] += 1
                    continue
                freeze = str(rows[0].get('featureHash') or '')
                if not freeze or freeze in seen:
                    counts['missing-or-repeated-hash'] += 1
                    continue
                seen.add(freeze)
                counts['exported-races'] += 1
                counts['exported-horses'] += len(rows)
                counts['jra-races' if str(rows[0].get('circuit') or '') in ('中央', 'JRA') else 'nar-races'] += 1
                for row in rows:
                    file.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    return {'status': 'research-export-only', 'productionChanged': False,
            'input': 'verified pre-off massFeatureArchive, settled labels',
            'counts': dict(sorted(counts.items())), 'output': str(destination)}


def main() -> int:
    p = argparse.ArgumentParser(description='Export verified MotherDuck frozen ranking labels, read-only')
    p.add_argument('output_jsonl')
    p.add_argument('--start-date', default=None)
    p.add_argument('--end-date', default=None)
    p.add_argument('--database', default='md:my_db')
    args = p.parse_args()
    # Research-only dependency; avoid installing into production PWA/Worker.
    import duckdb
    # MotherDuck uses local/CI credentials. Never include them in log output.
    con = duckdb.connect(args.database, read_only=True)
    try:
        cursor = con.execute(QUERY, [args.start_date, args.start_date, args.end_date, args.end_date])
        result = export(cursor, Path(args.output_jsonl))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        con.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
