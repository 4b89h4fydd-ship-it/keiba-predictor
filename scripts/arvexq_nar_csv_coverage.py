"""Read-only coverage audit for operator-provided NAR official archives.

Usage: python scripts/arvexq_nar_csv_coverage.py /path/to/nar.zip [more.zip ...]
The script does not download data or modify any race database or original file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from arvexq.databanks.nar_official_csv import rows_from_archive, race_key, item
from arvexq.ingest.nar_official_metadata import audit_official_race_metadata


def audit(paths):
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
    entries_by_race = Counter(race_key(h) for h in matched)
    no_horse_races = [key for key in races if not entries_by_race[key]]
    return {
        "sourceFiles": source_files,
        "raceMetadata": coverage,
        "horseRows": len(horses),
        "raceRowsWithHorseEntries": len(races) - len(no_horse_races),
        "raceRowsWithoutHorseEntries": len(no_horse_races),
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
    args = parser.parse_args()
    report = audit(args.archives)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
