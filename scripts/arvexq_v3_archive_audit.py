#!/usr/bin/env python3
"""Offline-only real archived racecard + snapshot manifest audit.

Only files that already exist under the repository are read. No HTTP calls,
no D1/SQLite writes, no model, marks or ticket generation.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.v3.audit.archive import audit_pair, summarize
from arvexq.v3.audit.calendar_window import calendar_window
from arvexq.v3.audit.payload import sample_saved_payloads

ARCHIVE = ROOT / "arvexq" / "ui" / "static"


def audit_days(*, directory: Path = ARCHIVE, days: int = 7, samples_per_circuit: int = 0, end_date: str | None = None) -> dict:
    if days < 1 or days > 31:
        raise ValueError("days must be between 1 and 31")
    existing = sorted(p for p in (directory / "racecards").glob("????-??-??.json")
                      if (directory / "saved-snapshots" / p.name).is_file())
    if end_date is not None:
        cutoff = date.fromisoformat(end_date).isoformat()
        existing = [p for p in existing if p.stem <= cutoff]
    if len(existing) < days:
        raise ValueError("insufficient saved daily racecards")
    reports = []
    for card_path in existing[-days:]:
        day = card_path.stem
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid saved day filename")
        manifest_path = directory / "saved-snapshots" / (day + ".json")
        if not manifest_path.is_file():
            raise ValueError(f"missing saved manifest for {day}")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        reports.append(audit_pair(card, manifest))
    report = summarize(reports)
    report["calendarWindow"] = calendar_window([p.stem for p in existing[-days:]])
    report["savedPayloadSample"] = sample_saved_payloads(directory, reports, samples_per_circuit)
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--archive-dir", type=Path, default=ARCHIVE)
    p.add_argument("--sample-per-circuit", type=int, default=1)
    p.add_argument("--out", type=Path, default=Path("arvexq-v3-archive-audit.json"))
    a = p.parse_args()
    try:
        result = audit_days(directory=a.archive_dir, days=a.days, samples_per_circuit=a.sample_per_circuit)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("ARVEXQ_V3_ARCHIVE_AUDIT_FAILED=" + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief = {k: result[k] for k in ("start", "end", "dateCount", "racecards", "manifestEntries", "circuits", "structuralProblems", "proofLimits", "savedPayloadSample")}
    print("ARVEXQ_V3_ARCHIVE_AUDIT_JSON=" + json.dumps(brief, ensure_ascii=False))
    return 1 if result["structuralProblems"] or result["savedPayloadSample"]["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
