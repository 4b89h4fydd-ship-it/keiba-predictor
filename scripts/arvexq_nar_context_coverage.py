#!/usr/bin/env python3
"""Read-only coverage audit of *already exported frozen* NAR mass features.

This does not retrain, replay past cards, claim original pre-off time witnesses,
write to D1, or convert source coverage into a hit-rate estimate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.mass_training_store import load_frozen_training_rows

FAMILIES = {
    "pace": ("nar::pace::",),
    "field_scenarios": ("nar::scenario::",),
    "sectional": ("nar::sectional::",),
    "trip": ("nar::trip::",),
    "bias": ("nar::bias::",),
    "jockey": ("nar::jockey::",),
    "transfer": ("nar::transfer::",),
    "odds": ("market::preoff_odds_",),
}
REQUIRED_SCHEMA = "arvexq-mass-features-v3-nar-provenanced-context"


def _valid_day(value: object) -> bool:
    try:
        return date.fromisoformat(str(value)).isoformat() == str(value)
    except (ValueError, TypeError):
        return False


def audit_rows(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    skipped = Counter()
    for row in rows:
        if not isinstance(row, dict) or str(row.get("circuit") or "") not in ("地方", "NAR", "nar"):
            skipped["non_nar_or_invalid"] += 1
            continue
        if "帯広" in str(row.get("track") or ""):
            skipped["banei"] += 1
            continue
        rid = str(row.get("raceId") or "")
        if not rid or not _valid_day(row.get("date")):
            skipped["invalid_identity"] += 1
            continue
        grouped[rid].append(row)

    eligible: list[list[dict]] = []
    for rid, race_rows in grouped.items():
        nums = [r.get("horseNumber") for r in race_rows]
        dates = {str(r.get("date")) for r in race_rows}
        hashes = {str(r.get("featureHash") or "") for r in race_rows}
        if (len(race_rows) < 3 or any(type(n) is not int or n <= 0 for n in nums)
                or len(set(nums)) != len(nums) or len(dates) != 1
                or len(hashes) != 1 or not next(iter(hashes))
                or sum(r.get("labelWin") == 1 for r in race_rows) != 1):
            skipped["incomplete_or_ambiguous_race"] += 1
            continue
        if any(str(r.get("schemaVersion") or "") != REQUIRED_SCHEMA for r in race_rows):
            skipped["old_or_mixed_schema"] += 1
            continue
        eligible.append(race_rows)

    horse_count = sum(len(group) for group in eligible)
    family_report = {}
    for name, prefixes in FAMILIES.items():
        horses = sum(
            any(str(key).startswith(prefixes) for key in (row.get("features") or {}))
            for group in eligible for row in group
        )
        races = sum(
            any(any(str(key).startswith(prefixes) for key in (row.get("features") or {}))
                for row in group)
            for group in eligible
        )
        family_report[name] = {
            "horses": horses, "races": races,
            "horseCoveragePct": round(100 * horses / horse_count, 2) if horse_count else None,
            "raceCoveragePct": round(100 * races / len(eligible), 2) if eligible else None,
        }
    with_context = sum(
        any(str(key).startswith("nar::") for key in (row.get("features") or {}))
        for group in eligible for row in group
    )
    days = sorted({str(group[0].get("date")) for group in eligible})
    return {
        "audit": "arvexq-nar-frozen-feature-coverage-v1",
        "status": "feature_corpus_present_not_preoff_proven" if with_context else "no_new_frozen_context_features",
        "observedRows": len(rows),
        "candidateRaces": len(grouped),
        "newSchemaRaces": len(eligible),
        "newSchemaHorseRows": horse_count,
        "contextHorseRows": with_context,
        "dates": len(days),
        "firstDate": days[0] if days else None,
        "lastDate": days[-1] if days else None,
        "families": family_report,
        "exclusions": dict(sorted(skipped.items())),
        "measuredAccuracy": None,
        "measuredROI": None,
        "note": "Original timestamp witness and independent held-out scored predictions are not supplied by training JSONL. Coverage only. Do not infer a hit rate.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check real frozen NAR context coverage without modifying data")
    parser.add_argument("source", help="Existing actual RaceDataBank SQLite or frozen training JSONL")
    parser.add_argument("--format", choices=("sqlite", "jsonl"), default="sqlite")
    args = parser.parse_args(argv)
    path = Path(args.source)
    if not path.is_file():
        parser.error(f"missing real input file: {path}")
    if args.format == "sqlite":
        rows = load_frozen_training_rows(path, circuit="地方")
    else:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(json.dumps(audit_rows(rows), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
