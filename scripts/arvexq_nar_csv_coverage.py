"""Read-only coverage audit for operator-provided NAR official archives.

Usage: python scripts/arvexq_nar_csv_coverage.py /path/to/nar.zip [more.zip ...]
The script does not download data or modify any race database or original file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

from arvexq.databanks.nar_official_csv import rows_from_archive, race_key, item
from arvexq.ingest.nar_official_metadata import audit_official_race_metadata


def audit(paths, target_date=None):
    races = {}
    horses = []
    source_files = []
    for path in paths:
        for filename, rows in rows_from_archive(path):
            source_files.append({"archive": str(path), "member": filename, "rows": len(rows)})
            if "racelist" in filename:
                for row in rows:
                    key = race_key(row)
                    if key[1] and key[2]:
                        races[key] = row
            elif "horselist" in filename:
                horses.extend(row for row in rows if race_key(row)[1])
    indexes = {"surface": 21, "direction": 22, "class_condition": 27}
    coverage = audit_official_race_metadata(list(races.values()), indexes)
    matched = [h for h in horses if race_key(h) in races]
    missing_race = len(horses) - len(matched)
    weights = sum(bool(item(h, 16).strip()) for h in matched)
    # Availability is measured from dated archive rows only. It does not
    # establish that a horse's lifetime career is fully represented.
    unique_starts = defaultdict(set)
    for h in matched:
        identity = (item(h, 6).strip(), item(h, 10).strip())
        unique_starts[identity].add(race_key(h))
    target_horses = {}
    if target_date:
        for h in matched:
            key = race_key(h)
            if key[1] != target_date:
                continue
            identity = (item(h, 6).strip(), item(h, 10).strip())
            earlier = {start for start in unique_starts[identity] if start[1] < target_date}
            target_horses[(key, int(item(h, 5) or 0))] = len(earlier)
    zero_history = sum(count == 0 for count in target_horses.values())
    entries_by_race = Counter(race_key(h) for h in matched)
    no_horse_races = [key for key in races if not entries_by_race[key]]
    missing_by_track = Counter(key[0] for key in no_horse_races)
    unmatched_by_track = Counter(race_key(h)[0] for h in horses if race_key(h) not in races)
    unmatched_race_keys = Counter(race_key(h) for h in horses if race_key(h) not in races)
    return {
        "sourceFiles": source_files,
        "raceMetadata": coverage,
        "horseRows": len(horses),
        "targetDate": target_date,
        "targetHorsesWithRaceRows": len(target_horses) if target_date else None,
        "targetHorsesWithNoEarlierArchiveRuns": zero_history if target_date else None,
        "targetHorsesWithEarlierArchiveRuns": len(target_horses) - zero_history if target_date else None,
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
    args = parser.parse_args()
    report = audit(args.archives, target_date=args.target_date)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
