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
    # A selected race needs the actual frozen horse-number picks and morning
    # marks. A ticket-kind label alone is not an actionable recommendation.
    # Older published archives remain first-write-wins; never backfill them.
    from datetime import datetime
    for r in rows:
        if r.get("morningSelected") is not True:
            continue
        e = r.get("morningTicketEvidence")
        if not isinstance(e, dict) or e.get("version") != "arvexq-morning-ticket-evidence-v1":
            print("MORNING_SELECTED_ORIGINAL_TICKETS_MISSING", r.get("id"))
            return None
        if str(e.get("raceId") or "") != str(r["id"]) or str(e.get("raceDate") or "") != str(r.get("date") or ""):
            return None
        try:
            post = datetime.fromisoformat(str(r["date"]) + "T" +
                   str(r.get("scheduledStartTime") or r.get("startTime") or "")[:5] + "+09:00")
            frozen = datetime.fromisoformat(str(e["fixedAt"]).replace("Z", "+00:00"))
            if not frozen.tzinfo or frozen >= post:
                return None
        except (ValueError, TypeError, KeyError):
            return None
        horses = e.get("marks")
        original_items = e.get("items")
        if not isinstance(horses, list) or len(horses) < 5 or not isinstance(original_items, list):
            return None
        nos = [int(h.get("horseNumber") or 0) for h in horses if isinstance(h, dict)]
        if len(nos) != len(horses) or len(set(nos)) != len(nos) or any(n <= 0 for n in nos):
            return None
        kinds = []
        valid_levels = {"本線", "保険", "3連単チャレンジ"}
        size_by_kind = {"ワイド": 2, "馬連": 2, "馬単": 2, "3連複": 3, "3連単": 3}
        main_found = False
        for item in original_items:
            if not isinstance(item, dict) or item.get("level") not in valid_levels or item.get("kind") not in size_by_kind:
                return None
            main_found = main_found or item["level"] == "本線"
            if item["kind"] not in kinds:
                kinds.append(item["kind"])
            combos = item.get("combos")
            if not isinstance(combos, list) or not combos:
                return None
            if item["kind"] == "3連単" and not 6 <= len(combos) <= 12:
                return None
            for combo in combos:
                if (not isinstance(combo, list) or len(combo) != size_by_kind[item["kind"]]
                    or len(set(combo)) != len(combo) or not set(combo).issubset(set(nos))):
                    return None
        if not main_found or set(kinds) != set(e.get("ticketKinds") or []) or set(kinds) != set(r.get("morningTicketKinds") or []):
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
                 "ticketKinds": r.get("morningTicketKinds") or [],
                 "selectionModelVersion": ((r.get("volatility") or {}).get("morningPicks") or {}).get("selectionModelVersion") or "",
                 "ticketEvidence": r.get("morningTicketEvidence") if r["morningSelected"] else None}
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
