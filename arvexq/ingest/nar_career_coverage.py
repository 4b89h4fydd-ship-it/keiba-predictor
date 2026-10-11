"""Conservative, race-date-specific NAR local career search stopping rule.

A runner's five latest starts never prove lifetime completeness. This module
does not invent starts or imply that a finite monthly lookback is a full career.
"""
from __future__ import annotations
from typing import Any
from threading import BoundedSemaphore

# Avoid 80 race background workers each spawning up to six official ZIP fetches.
# Limit network-heavy monthly waves while retaining independent, safe DB I/O.
nar_history_wave_slots = BoundedSemaphore(2)
from arvexq.ingest.full_career import date_key


def pre_race_reported_starts(detail: dict[str, Any] | None, cutoff: str,
                             horse_names: list[str]) -> dict[str, int]:
    """Get verified as-of-race start-count targets without using later results."""
    end=date_key(cutoff)
    if not isinstance(detail,dict) or not end:
        return {}
    selected=set(str(x) for x in horse_names if x)
    horses=[h for h in (detail.get("horses") or []) if isinstance(h,dict)]
    counts: dict[str,int]={}
    duplicates: set[str]=set()
    for horse in horses:
        name=str(horse.get("name") or "")
        if not name or name not in selected:
            continue
        if name in counts:
            duplicates.add(name)
            continue
        sources=[horse.get("careerStartEvidence"),horse.get("_careerHistoryAudit")]
        for source in sources:
            if not isinstance(source,dict) or source.get("conflict") or source.get("reportedStartsConflict"):
                continue
            as_of=date_key(source.get("asOfRaceDate") or source.get("requestedAtRaceDate"))
            if as_of != end:
                continue
            value=source.get("starts") if "starts" in source else source.get("reportedStarts")
            if type(value) is int and value>=0:
                counts[name]=value
                break
    for name in duplicates:
        counts.pop(name,None)
    return counts


def official_history_complete(coverage: dict[str,Any], required: dict[str,int]) -> bool:
    """Full coverage requires date-bound totals for every runner; unknown=not ready."""
    counts=coverage.get("counts") or {}
    if not isinstance(counts,dict) or not counts:
        return False
    if any(name not in required or type(required[name]) is not int
           or required[name]<0 for name in counts):
        return False
    return all(int(count or 0)==required[name] for name,count in counts.items())
