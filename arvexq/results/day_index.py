"""Small verified race-index recovery for the existing result updater.

The file is an output of the canonical racecard prefetch, not a data provider.
It only supplies race IDs when the D1 summary list is empty.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def restore_if_empty(bundle: dict[str, Any], target_date: str, archive: Path) -> tuple[dict[str, Any], str]:
    current = bundle.get("races")
    if isinstance(current, list) and current:
        return bundle, "d1"
    if not archive.is_file():
        return bundle, "no-verified-racecard-archive"
    try:
        published = json.loads(archive.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return bundle, "invalid-racecard-archive"
    rows = published.get("races")
    if (published.get("version") != "arvexq-static-entry-v1" or
            published.get("date") != target_date or not isinstance(rows, list)):
        return bundle, "invalid-racecard-archive"
    valid = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or "")
        if (not rid.startswith(("jra-"+target_date+"-", "nar-"+target_date+"-"))
                or str(row.get("date") or "") != target_date
                or not row.get("track") or not row.get("raceNumber") or rid in seen):
            continue
        valid.append(row)
        seen.add(rid)
    if not valid or len(valid) != len(rows):
        return bundle, "incomplete-racecard-archive"
    out = dict(bundle)
    out["date"] = target_date
    out["races"] = valid
    out["details"] = list(bundle.get("details") or [])
    return out, "verified-canonical-racecard-archive"
