#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble a lane day bundle from the committed static API packs.

Cloudflare-exit counterpart of scripts/arvexq_fetch_d1_bundle.py: same
output contract ({date, races, details} plus the day body's own fields)
and the same report shape, but the source is the in-repo static pack
tree (arvexq/ui/static/api-static) instead of the D1-backed Worker API.

The packs are built from the very payloads the lanes produce, so a day
that the lanes have published is fully reconstructible from the repo:
  day/<date>.json   -> races (the /api/day?details=0 summary rows)
  race/<race_id>.json -> detail (the /api/race body"s "detail" member)

Known, deliberate delta vs the D1 read: pack details have the
``massFeatureSnapshot`` field stripped (the pack builder mirrors the
public display view, which strips it server-side too).  Consumers of
this bundle (result repair, live sync) merge volatile/result fields
into the base and never republish the snapshot field, so nothing the
packs themselves carry is lost.

Retired Banei (Obihiro) summaries are excluded on this path too, with
the same rule as the D1 fetcher.  Nothing is invented: a race whose
pack file is absent or malformed is reported as a missing detail, and
the caller decides (via --allow-missing-details) whether that is fatal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _is_retired_banei(row: dict[str, Any]) -> bool:
    rid = str(row.get("id") or "")
    return (
        str(row.get("track") or "") in ("帯広", "帯広ば")
        or "-帯広-" in rid
        or "-帯広ば-" in rid
    )


def build_bundle(packs_dir: Path, date: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns (bundle, report).  Raises FileNotFoundError when the day
    pack itself is absent; the caller maps that to the empty-day path."""
    day_path = packs_dir / "day" / f"{date}.json"
    if not day_path.is_file():
        raise FileNotFoundError(f"no day pack for {date}: {day_path}")
    day = json.loads(day_path.read_text(encoding="utf-8"))
    if not isinstance(day, dict):
        raise ValueError(f"day pack for {date} is not a JSON object")
    observed_date = str(day.get("date") or "")
    if observed_date and observed_date != date:
        raise ValueError(f"day pack date mismatch: {observed_date} != {date}")

    all_races = [r for r in (day.get("races") or []) if isinstance(r, dict) and r.get("id")]
    retired = [r for r in all_races if _is_retired_banei(r)]
    races = [r for r in all_races if r not in retired]

    details: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for row in races:
        rid = str(row["id"])
        race_path = packs_dir / "race" / f"{rid}.json"
        try:
            body = json.loads(race_path.read_text(encoding="utf-8"))
            detail = body.get("detail") if isinstance(body, dict) else None
            if not isinstance(detail, dict):
                errors[rid] = "race pack has no detail object"
                continue
            if str(detail.get("id") or "") != rid:
                errors[rid] = "race pack detail identity mismatch"
                continue
            details.append(detail)
        except FileNotFoundError:
            errors[rid] = "race pack absent"
        except Exception as exc:  # malformed pack JSON etc.
            errors[rid] = f"{type(exc).__name__}: {exc}"

    bundle = dict(day)
    bundle["date"] = date
    bundle["races"] = races
    bundle["details"] = details
    report = {
        "date": date,
        "source": "static-packs",
        "race_count": len(races),
        "detail_count": len(details),
        "retired_banei_excluded_count": len(retired),
        "missing_detail_count": len(errors),
        "missing_details": [
            {"race_id": str(r["id"]), "error": errors[str(r["id"])]}
            for r in races
            if str(r["id"]) in errors
        ],
    }
    if retired:
        print(
            "PACK_RETIRED_BANEI_SUMMARIES_IGNORED",
            len(retired),
            [r["id"] for r in retired],
        )
    return bundle, report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--packs", default="arvexq/ui/static/api-static",
                   help="static pack tree root (contains day/ and race/)")
    p.add_argument("--date", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report", default="")
    p.add_argument("--allow-missing-details", action="store_true")
    p.add_argument("--allow-empty-day", action="store_true",
                   help="Accept an explicitly empty day (no day pack yet) "
                        "for cold-start publication, mirroring the D1 fetcher")
    args = p.parse_args()

    packs_dir = Path(args.packs)
    try:
        bundle, report = build_bundle(packs_dir, args.date)
    except FileNotFoundError:
        if not args.allow_empty_day:
            raise SystemExit(f"No day pack for {args.date} under {packs_dir}")
        bundle = {"date": args.date, "races": [], "details": []}
        report = {"date": args.date, "source": "static-packs",
                  "race_count": 0, "detail_count": 0,
                  "retired_banei_excluded_count": 0,
                  "missing_detail_count": 0, "missing_details": [],
                  "empty_day": True}
        Path(args.out).write_text(
            json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        if args.report:
            Path(args.report).write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("PACK_EMPTY_DAY_READY_FOR_INITIAL_PUBLICATION", args.date)
        return 0

    Path(args.out).write_text(
        json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    if args.report:
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "PACK_BUNDLE_AUDIT",
        f"races={report['race_count']}",
        f"details={report['detail_count']}",
        f"missing={report['missing_detail_count']}",
    )
    if report["missing_detail_count"] and not args.allow_missing_details:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
