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
    found: dict[str, dict[str, Any]] = {}
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
        # A horse cannot have two starts on the same calendar date.
        # Date-only identity also deduplicates feeds that omit track or race ID.
        key = at
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
    end = date_key(cutoff)
    runs = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), cutoff)
    stats = next((horse[k] for k in ("careerStartEvidence", "careerStats")
                  if isinstance(horse.get(k), dict) and horse[k].get("asOfRaceDate") == end), {})
    # A start count is evidence only for the race date it was computed for.
    # Legacy counts without asOfRaceDate may include later starts.
    bound = stats.get("asOfRaceDate") == end and not stats.get("conflict")
    declared = next((int(stats[k]) for k in ("starts", "totalStarts", "careerStarts")
                     if bound and str(stats.get(k) if stats.get(k) is not None else "").isdigit()), None)
    observed_dates = {r["date"] for r in runs}
    listed = stats.get("startDates") if bound and isinstance(stats.get("startDates"), list) else None
    unobserved = sorted(set(listed) - observed_dates) if listed is not None else None
    unexpected = sorted(observed_dates - set(listed)) if listed is not None else None
    missing = max(0, declared - len(runs)) if declared is not None else None
    dates_ok = listed is None or (not unobserved and not unexpected)
    complete = declared is not None and len(runs) == declared and dates_ok
    return {
        "version": "arvexq-career-coverage-v1", "observedRuns": len(runs),
        "requestedLimit": requested, "requestedAtRaceDate": end,
        "providersAttempted": sorted(set(providers)),
        "reportedStarts": declared, "unobservedMinimum": missing,
        "reportedStartsSource": stats.get("source") if declared is not None else None,
        "reportedStartsConflict": bool(stats.get("conflict")) and stats.get("asOfRaceDate") == end,
        "unobservedDates": unobserved, "unexpectedDates": unexpected,
        # Exact equality only: more observed rows than reported starts means the
        # count source or the deduplication cannot be trusted as proof.
        "complete": complete,
        "status": ("missing" if not runs and declared != 0 else
                   "unverified" if declared is None else
                   "incomplete" if missing or unobserved else
                   "count-mismatch" if not complete else "reported-starts-covered"),
    }
