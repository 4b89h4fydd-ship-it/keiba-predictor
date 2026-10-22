"""Read-only coverage audit for operator-provided NAR official archives.

Usage: python scripts/arvexq_nar_csv_coverage.py /path/to/nar.zip [more.zip ...]
The script does not download data or modify any race database or original file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from arvexq.databanks.nar_official_csv import rows_from_archive, race_key, item, NarOfficialArchive, number, date
from arvexq.components.item_021.nar_official_metadata import audit_official_race_metadata


def audit(paths, target_date=None):
    archive = NarOfficialArchive(paths)
    races = archive.race_rows
    horses = list(archive.entry_rows.values())
    source_files = []
    for path in paths:
        for filename, rows in rows_from_archive(path):
            source_files.append({"archive": str(path), "member": filename, "rows": len(rows)})
    indexes = {"surface": 21, "direction": 22, "class_condition": 27}
    coverage = audit_official_race_metadata(list(races.values()), indexes)
    matched = [h for h in horses if race_key(h) in races]
    missing_race = len(horses) - len(matched)
    weights = sum(bool(item(h, 16).strip()) for h in matched)
    # Availability is measured from dated archive rows only. It does not
    # establish that a horse's lifetime career is fully represented.
    target_horses = {}
    if target_date:
        for h in matched:
            key = race_key(h)
            if key[1] != target_date:
                continue
            history = archive.horse_history(
                {"name": item(h, 6), "birthDate": date(item(h, 10))},
                {"date": target_date})
            target_horses[(key, number(item(h, 5)))] = len([
                r for r in history.get("allPastRuns", []) if r.get("finish", 0) > 0])
    zero_history = sum(count == 0 for count in target_horses.values())
    history_counts = Counter(target_horses.values())
    low_history = sum(count < 5 for count in target_horses.values())
    entries_by_race = Counter(race_key(h) for h in matched)
    no_horse_races = [key for key in races if not entries_by_race[key]]
    missing_by_track = Counter(key[0] for key in no_horse_races)
    unmatched_by_track = Counter(race_key(h)[0] for h in horses if race_key(h) not in races)
    unmatched_race_keys = Counter(race_key(h) for h in horses if race_key(h) not in races)
    target_keys = [k for k in races if not target_date or k[1] == target_date]
    target_key_set = set(target_keys)
    target_entries = [h for h in matched if race_key(h) in target_key_set]
    target_expected = sum(number(item(races[k], 26)) for k in target_keys)
    mismatches = [{"race": list(k), "reportedFieldSize": number(item(races[k], 26)),
                   "acquiredEntries": entries_by_race[k]}
                  for k in target_keys if number(item(races[k], 26)) != entries_by_race[k]]
    return {
        "targetRaces": len(target_keys),
        "targetReportedFieldSizeTotal": target_expected,
        "targetAcquiredEntries": len(target_entries),
        "targetEntryCoveragePercent": round(100*len(target_entries)/target_expected, 2) if target_expected else None,
        "targetFieldSizeMismatches": mismatches,
        "targetEntryMissingFields": {name: sum(not item(h, offset) for h in target_entries)
            for name, offset in (("birthDate",10),("jockey",14),("trainer",18),("carriedWeight",16))},
        "sourceFiles": source_files,
        "raceMetadata": coverage,
        "horseRows": len(horses),
        "targetDate": target_date,
        "targetHorsesWithRaceRows": len(target_horses) if target_date else None,
        "targetHorsesWithNoEarlierArchiveRuns": zero_history if target_date else None,
        "targetHorsesWithEarlierArchiveRuns": len(target_horses) - zero_history if target_date else None,
        "targetHorsesWithFewerThanFiveEarlierRuns": low_history if target_date else None,
        "targetHistoryObservedRunCountDistribution": dict(sorted(history_counts.items())) if target_date else None,
        "raceRowsWithHorseEntries": len(races) - len(no_horse_races),
        "raceRowsWithoutHorseEntries": len(no_horse_races),
        "raceRowsWithoutHorseEntriesByTrack": dict(sorted(missing_by_track.items())),
        "unmatchedHorseRowsByTrack": dict(sorted(unmatched_by_track.items())),
        "unmatchedHorseRaceKeys": [{"track": key[0], "date": key[1], "raceNumber": key[2], "horseRows": count} for key, count in sorted(unmatched_race_keys.items())],
        "raceKeysWithoutHorseEntries": [list(key) for key in sorted(no_horse_races)],
        "horseRowsMatchingRacePercent": round(len(matched) * 100 / len(horses), 2) if horses else None,
        "horseRowsWithRace": len(matched),
        "horseRowsWithoutRace": missing_race,
        "horseRowsWithCarriedWeight": weights,
        "horseRowsMissingCarriedWeight": len(matched) - weights,
        "tracks": dict(sorted(Counter(k[0] for k in races).items())),
        "limitations": [
            "Coverage describes supplied CSV records, not all scheduled NAR races.",
            "Horse-history completeness requires dated pre-race career-start evidence.",
            "No pre-off prediction accuracy is estimated from these records.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", help="Local NAR official CSV ZIP or directory")
    parser.add_argument("--output", help="Optional JSON report path")
    parser.add_argument("--target-date", help="Target race date YYYY-MM-DD for prior-run coverage")
    parser.add_argument("--require-prior-history", action="store_true", help="Fail when any target runner lacks an earlier observed archive run; requires --target-date")
    parser.add_argument("--min-races", type=int, default=0, help="Minimum target races for acceptance")
    parser.add_argument("--min-prior-runs", type=int, default=0, help="Minimum observed earlier archive starts per target horse (requires --target-date); does not prove full career")
    args = parser.parse_args()
    if args.min_races < 0:
        parser.error("--min-races must be nonnegative")
    if args.min_prior_runs < 0:
        parser.error("--min-prior-runs must be nonnegative")
    if (args.require_prior_history or args.min_prior_runs) and not args.target_date:
        parser.error("--require-prior-history requires --target-date")
    report = audit(args.archives, target_date=args.target_date)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if args.min_races and (report['targetRaces'] < args.min_races or report['targetFieldSizeMismatches']):
        raise SystemExit(1)
    if args.require_prior_history and (not report["targetHorsesWithRaceRows"] or report["targetHorsesWithNoEarlierArchiveRuns"]):
        raise SystemExit(1)
    if args.min_prior_runs and (not report["targetHorsesWithRaceRows"] or any(int(count) < args.min_prior_runs and number > 0 for count, number in report["targetHistoryObservedRunCountDistribution"].items())):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
