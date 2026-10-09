#!/usr/bin/env python3
"""Write a first-complete-dawn selection manifest as a public static asset.

Cloudflare D1 /api/sync strips non-schema pick fields. Static versioned assets
are therefore the durable canonical store for once-only race membership.
No post-off, incomplete or absent predictions are backfilled.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def morning_manifest(payload: dict) -> dict | None:
    rows = [r for r in payload.get("summaries") or [] if isinstance(r, dict) and r.get("id")]
    details = {str(d.get("id")): d for d in payload.get("details") or []
               if isinstance(d, dict) and d.get("id")}
    if not rows or len(details) < len(rows):
        return None
    dates = {str(r.get("date") or "") for r in rows}
    captured = {str(r.get("morningPickFixedAt") or "") for r in rows}
    if len(dates) != 1 or "" in dates or len(captured) != 1 or "" in captured:
        return None
    if not all(r.get("morningPickVersion") == "v1" and
               isinstance(r.get("morningSelected"), bool) and
               isinstance(r.get("morningSpecial"), bool) and
               int(r.get("morningPickScope") or 0) == len(rows)
               for r in rows):
        return None
    if any(str(r.get("id")) not in details for r in rows):
        return None
    return {"version": "v1", "date": next(iter(dates)),
            "fixedAt": next(iter(captured)), "scope": len(rows),
            "races": [
                {"id": str(r["id"]),
                 "selected": r["morningSelected"],
                 "selectedScore": r.get("morningSelectedScore") or 0,
                 "special": r["morningSpecial"],"assessed":r.get("morningAssessed") is not False,
                 "primaryType": r.get("morningPrimaryType") or "",
                 "types": r.get("morningSelectedTypes") or [],
                 "selectionReason": r.get("morningSelectionReason") or "",
                 "selectionModelVersion": ((r.get("volatility") or {}).get("morningPicks") or {}).get("selectionModelVersion") or ""}
                for r in rows
            ]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default="arvexq/ui/static/morning-picks")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    manifest = morning_manifest(payload)
    if manifest is None:
        print("STATIC_MORNING_PICKS_NOT_AVAILABLE_NO_POST_HOC")
        return 0
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (manifest["date"] + ".json")
    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old != manifest:
            print("STATIC_MORNING_PICKS_ALREADY_FROZEN_FIRST_WINS", path)
        else:
            print("STATIC_MORNING_PICKS_ALREADY_SAVED", path)
        return 0
    path.write_text(encoded, encoding="utf-8")
    print("STATIC_MORNING_PICKS_CREATED", path,
          "races", manifest["scope"],
          "selected", sum(x["selected"] for x in manifest["races"]),
          "special", sum(x["special"] for x in manifest["races"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
