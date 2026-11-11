#!/usr/bin/env python3
"""Validate a dated v26 sealed-marks archive.

The v26 shadow lane's dated archives live in
``arvexq/ui/static/v26-marks/<YYYY-MM-DD>.json`` and are consumed
read-only by the web UI and the morning freeze. Until 2026-11-11 the
archives arrived as externally produced data commits; when the
2026-11-11 archive never arrived, nothing in the repository noticed
and the UI hid the v26 column silently.

This script is the in-repo contract for those archives. It never
creates or alters marks: a missing or malformed archive is reported
as a failure (exit 1) with the reason, so the watchdog workflow can
surface it before the day's first race instead of after it.

Usage:
    python3 scripts/arvexq_v26_marks_archive.py [--date YYYY-MM-DD]
                                                 [--archive-dir DIR]

Without --date, today's date in Asia/Tokyo is used.
Exit codes: 0 = archive present and valid, 1 = missing/invalid.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

VALID_MARKS = {"◎", "○", "▲", "△", "☆"}
REQUIRED_RACE_KEYS = {"marks", "signals"}


def archive_path(archive_dir: Path, date: str) -> Path:
    return archive_dir / f"{date}.json"


def validate_archive(path: Path, date: str) -> list[str]:
    """Return a list of problems; an empty list means valid."""
    if not path.is_file():
        return [f"missing: {path} does not exist"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"invalid: cannot parse {path}: {exc}"]
    if not isinstance(payload, dict):
        return ["invalid: top level is not a JSON object"]
    problems: list[str] = []
    if payload.get("date") != date:
        problems.append(
            f"invalid: date field is {payload.get('date')!r}, expected {date!r}")
    races = payload.get("races")
    if not isinstance(races, dict) or not races:
        problems.append("invalid: races is missing, not an object, or empty")
        return problems
    race_count = payload.get("raceCount")
    if race_count != len(races):
        problems.append(
            f"invalid: raceCount is {race_count!r} but races has {len(races)} entries")
    for race_id, entry in races.items():
        if not isinstance(entry, dict):
            problems.append(f"invalid: race {race_id} entry is not an object")
            continue
        missing = REQUIRED_RACE_KEYS - set(entry)
        if missing:
            problems.append(
                f"invalid: race {race_id} is missing keys {sorted(missing)}")
            continue
        marks = entry["marks"]
        if not isinstance(marks, dict) or not marks:
            problems.append(f"invalid: race {race_id} marks are empty")
            continue
        for number, mark in marks.items():
            if not str(number).isdigit():
                problems.append(
                    f"invalid: race {race_id} has a non-numeric horse key {number!r}")
            if mark not in VALID_MARKS:
                problems.append(
                    f"invalid: race {race_id} horse {number} has unknown mark {mark!r}")
        if not isinstance(entry["signals"], dict):
            problems.append(f"invalid: race {race_id} signals are not an object")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=None,
                        help="archive date YYYY-MM-DD (default: today, Asia/Tokyo)")
    parser.add_argument("--archive-dir", default=None,
                        help="directory holding the dated archives "
                             "(default: arvexq/ui/static/v26-marks)")
    args = parser.parse_args(argv)
    date = args.date or datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    root = Path(__file__).resolve().parent.parent
    archive_dir = (Path(args.archive_dir) if args.archive_dir
                   else root / "arvexq" / "ui" / "static" / "v26-marks")
    path = archive_path(archive_dir, date)
    problems = validate_archive(path, date)
    if problems:
        for problem in problems:
            print(f"v26-archive {date}: {problem}", file=sys.stderr)
        return 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    print(f"v26-archive {date}: ok ({payload.get('raceCount')} races, "
          f"modelKey={payload.get('modelKey')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
