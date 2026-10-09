"""Date-bounded observed career history. Unknown coverage is never called complete."""
from __future__ import annotations
import copy
import re
from datetime import date
from typing import Any

def date_key(value: Any) -> str:
    raw = str(value or "").strip().replace("/", "-").replace(".", "-")
    if re.fullmatch(r"\d{8}", raw):
        raw = raw[:4] + "-" + raw[4:6] + "-" + raw[6:]
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except (TypeError, ValueError):
        return ""

def merge_career(existing: Any, incoming: Any, cutoff: str) -> list[dict[str, Any]]:
    end = date_key(cutoff)
    if not end:
        return []
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in [*(existing if isinstance(existing, list) else []),
                *(incoming if isinstance(incoming, list) else [])]:
        if not isinstance(raw, dict):
            continue
        at = date_key(raw.get("date") or raw.get("raceDate") or raw.get("日付"))
        if not at or at >= end:
            continue
        item = copy.deepcopy(raw)
        item["date"] = at
        # A horse cannot have multiple starts on the same day. Merge complementary
        # source fields instead of double counting conflicting provider identities.
        key = (at, str(item.get("track") or item.get("venue") or item.get("course") or ""))
        if key not in found:
            found[key] = item
            continue
        saved = found[key]
        for name, value in item.items():
            if name in ("cornerPositions", "passing") and isinstance(value, list):
                previous = saved.get(name)
                if not isinstance(previous, list):
                    saved[name] = copy.deepcopy(value)
                else:
                    saved[name] = [
                        v if v not in (None, "", 0) else (value[i] if i < len(value) else v)
                        for i, v in enumerate(previous + [None] * max(0, len(value) - len(previous)))
                    ]
            elif saved.get(name) in (None, "", [], {}) and value not in (None, "", [], {}):
                saved[name] = copy.deepcopy(value)
    return sorted(found.values(), key=lambda x: x["date"], reverse=True)

def audit_career(horse: dict[str, Any], cutoff: str, requested: int,
                 providers: list[str]) -> dict[str, Any]:
    runs = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)
    stats = horse.get("careerStats") if isinstance(horse.get("careerStats"), dict) else {}
    declared = next((int(stats[k]) for k in ("starts", "totalStarts", "careerStarts")
                     if str(stats.get(k) or "").isdigit()), None)
    missing = max(0, declared - len(runs)) if declared is not None else None
    return {
        "version": "arvexq-career-coverage-v1", "observedRuns": len(runs),
        "requestedLimit": requested, "requestedAtRaceDate": date_key(cutoff),
        "providersAttempted": sorted(set(providers)),
        "reportedStarts": declared, "unobservedMinimum": missing,
        "complete": declared is not None and len(runs) >= declared,
        "status": ("missing" if not runs else "incomplete" if missing else
                   "unverified" if declared is None else "reported-starts-covered"),
    }
