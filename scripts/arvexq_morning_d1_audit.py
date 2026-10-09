#!/usr/bin/env python3
"""Audit a Cloudflare D1 day against immutable first-write-wins morning picks.

D1's /api/sync summary schema currently omits morning-pick extras.
Never repair by overwriting historic selections or creating post-off picks.
The separately deployed immutable static archive is the public authority.
Distinguish a schema-omitted projection from a contradictory record.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

SUPPORTED_TYPES = {"的中重視型", "勝ち馬明確型", "高配当狙い型"}


def saved_projection(row: dict[str, Any]) -> dict[str, Any] | None:
    for name in ("volatility", "environmentMeta"):
        source = row.get(name)
        val = source.get("morningPicks") if isinstance(source, dict) else None
        if isinstance(val, dict) and val.get("version") == "v1":
            return val
    if row.get("morningPickVersion") == "v1":
        return {"version": "v1", "fixedAt": row.get("morningPickFixedAt"),
                "selected": row.get("morningSelected"),
                "selectedScore": row.get("morningSelectedScore"),
                "special": row.get("morningSpecial"),
                "primaryType": row.get("morningPrimaryType") or "",
                "types": row.get("morningSelectedTypes") or [],
                "ticketKinds": row.get("morningTicketKinds") or []}
    return None


def validate(manifest: dict[str, Any], d1: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("version") != "v1" or not manifest.get("fixedAt"):
        raise ValueError("immutable morning manifest missing version/fixedAt")
    day = str(manifest.get("date") or "")
    manifest_rows = manifest.get("races")
    if not isinstance(manifest_rows, list) or len(manifest_rows) != manifest.get("scope"):
        raise ValueError("morning manifest has a broken race scope")
    expected = {str(row.get("id") or ""): row for row in manifest_rows
                if isinstance(row, dict) and row.get("id")}
    if len(expected) != len(manifest_rows):
        raise ValueError("morning manifest has duplicate or empty race IDs")
    for rid, row in expected.items():
        types = row.get("types") or []
        kinds = row.get("ticketKinds") or []
        if row.get("selected") is True and (not types or not kinds):
            # pre-v2 fixed records remain immutable; classify as legacy.
            continue
        if any(t not in SUPPORTED_TYPES for t in types):
            raise ValueError("unknown morning type " + rid)
    d1_rows = d1.get("races") or []
    if not isinstance(d1_rows, list):
        raise ValueError("D1 day races is not an array")
    if d1.get("date") and str(d1["date"]) != day:
        raise ValueError("D1 racing day does not match immutable manifest")
    d1_by_id = {str(row.get("id") or ""): row for row in d1_rows
                if isinstance(row, dict) and row.get("id")}
    absent, omitted, conflict, verified = [], [], [], []
    for rid, original in expected.items():
        actual = d1_by_id.get(rid)
        if actual is None:
            absent.append(rid)
            continue
        stored = saved_projection(actual)
        if not stored:
            omitted.append(rid)
            continue
        same = (
            str(stored.get("version") or "") == "v1"
            and str(stored.get("fixedAt") or "") == str(manifest["fixedAt"])
            and stored.get("selected") is original.get("selected")
            and stored.get("special") is original.get("special")
            and float(stored.get("selectedScore") or 0) == float(original.get("selectedScore") or 0)
        )
        for key in ("primaryType", "types", "ticketKinds"):
            if key in stored and stored.get(key) != original.get(key):
                same = False
        (verified if same else conflict).append(rid)
    return {
        "version": "arvexq-static-morning-d1-audit-v1",
        "date": day, "authority": "immutable-static-manifest",
        "manifestRaceCount": len(expected),
        "d1RaceCount": len(d1_by_id),
        "verifiedInD1": len(verified),
        "schemaOmittedInD1": len(omitted),
        "contradictoryInD1": conflict,
        "missingD1Races": absent,
        "manifestSelected": sum(row.get("selected") is True for row in manifest_rows),
        "legacyUnverifiedSelections": sum(row.get("selected") is True and
            (not row.get("types") or not row.get("ticketKinds")) for row in manifest_rows),
        "safeToDisplayFromStatic": not absent and not conflict and len(expected)>0,
        "writePolicy": "read-only-never-retroactively-rewrite",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--d1", required=True)
    parser.add_argument("--report", default="morning-d1-audit.json")
    args = parser.parse_args()
    result = validate(json.loads(Path(args.manifest).read_text(encoding="utf-8")),
                      json.loads(Path(args.d1).read_text(encoding="utf-8")))
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("MORNING_D1_AUDIT", json.dumps(result, ensure_ascii=False))
    # Schema omission is currently an acknowledged Worker limitation; a truly
    # contradictory race or a missing D1 race is a hard issue.
    return 0 if result["safeToDisplayFromStatic"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
