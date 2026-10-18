#!/usr/bin/env python3
"""Offline verify deterministic bounded samples of original archived gzip data."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.v3.audit.snapshot_digest import audit_saved_blobs

ARCHIVE = ROOT / "arvexq" / "ui" / "static"


def audit_days(directory: Path = ARCHIVE, *, days: int = 7, per_circuit: int = 2) -> dict:
    if isinstance(days, bool) or not 1 <= days <= 31:
        raise ValueError("days must be 1..31")
    if isinstance(per_circuit, bool) or not 1 <= per_circuit <= 6:
        raise ValueError("per_circuit must be 1..6")
    existing = sorted(p for p in (directory / "racecards").glob("????-??-??.json")
                      if (directory / "saved-snapshots" / p.name).is_file())
    if len(existing) < days:
        raise ValueError("insufficient saved racecard days")
    reports = []
    for path in existing[-days:]:
        day = path.stem
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid saved day filename")
        manifest_path = directory / "saved-snapshots" / (day + ".json")
        card = json.loads(path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        reports.append(audit_saved_blobs(directory, card, manifest,
                                        per_circuit=per_circuit))
    circuit = {}
    for name in ("jra", "nar"):
        circuit[name] = {
            "checked": sum(d["counts"][name].get("checked", 0) for d in reports),
            "verified": sum(d["counts"][name].get("verified", 0) for d in reports),
            "failed": sum(d["counts"][name].get("failed", 0) for d in reports),
        }
    return {
        "schema": "arvexq-v3-snapshot-sha256-week-sample-audit-1",
        "start": reports[0]["date"], "end": reports[-1]["date"],
        "circuits": circuit,
        "samples": reports,
        "allSampledVerified": all(d["allSampledVerified"] for d in reports),
        "fullArchiveVerified": False,
        "liveApi429Resolved": False,
        "predictionStatus": "not-implemented",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--per-circuit", type=int, default=2)
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE)
    parser.add_argument("--out", type=Path, default=Path("arvexq-v3-blob-audit.json"))
    args = parser.parse_args()
    try:
        report = audit_days(args.archive_dir, days=args.days,
                            per_circuit=args.per_circuit)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ARVEXQ_V3_BLOB_AUDIT_FAILED={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ARVEXQ_V3_BLOB_AUDIT_JSON=" + json.dumps({
        "start": report["start"], "end": report["end"],
        "circuits": report["circuits"],
        "allSampledVerified": report["allSampledVerified"],
        "fullArchiveVerified": report["fullArchiveVerified"],
    }, ensure_ascii=False))
    return 0 if report["allSampledVerified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
