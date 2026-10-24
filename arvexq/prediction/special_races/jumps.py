"""JRA jump-race evidence box; do not substitute flat-race performance."""
from __future__ import annotations

import re
from typing import Any

_JUMP = re.compile(r"障害|ジャンプ|J[･・.]?G[ⅠⅡⅢ123]", re.I)
_SOURCE_KEYS = {
    "jumpStats": ("jumpStats",),
    "jumpJockeyStats": ("jumpJockeyStats",),
    "jumpTrainerStats": ("jumpTrainerStats",),
    "jumpTrial": ("jumpTrial", "jumpTest", "obstacleTrial"),
    "jumpWorkout": ("jumpWorkout", "jumpTraining", "jumpWorkouts"),
}


def _jump_run(run: dict[str, Any]) -> bool:
    return str(run.get("analysisMode") or "") == "障害" or bool(
        _JUMP.search(str(run.get("title") or run.get("raceName") or ""))
        or "障" in str(run.get("surface") or "")
    )


def _prior_history(horse: dict[str, Any], date: str) -> tuple[list[dict[str, Any]], bool]:
    raw = horse.get("allPastRuns")
    if not isinstance(raw, list):
        raw = horse.get("recentRaces")
    if not isinstance(raw, list):
        return [], False
    # Only dated, strictly earlier observations may contribute to the audit.
    return ([run for run in raw if isinstance(run, dict)
             and str(run.get("date") or run.get("raceDate") or "")[:10]
             and str(run.get("date") or run.get("raceDate"))[:10] < date], True)


def build_jump_box(detail: dict[str, Any]) -> dict[str, Any]:
    rows = []
    day = str(detail.get("date") or "")[:10]
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict) or not horse.get("horseNumber") or horse.get("scratched"):
            continue
        raw, has_visible_history = _prior_history(horse, day)
        jump_runs = [r for r in raw if _jump_run(r)]
        present = [key for key, aliases in _SOURCE_KEYS.items()
                   if any(k in horse and horse[k] not in (None, "", [], {}) for k in aliases)]
        packed = bool(horse.get("careerTransport") or horse.get("careerArchive"))
        rows.append({
            "horseNumber": int(horse["horseNumber"]),
            "name": str(horse.get("name") or ""),
            "observedFields": present,
            "missingFields": [k for k in _SOURCE_KEYS if k not in present],
            "jumpRunsDatedBeforeRace": len(jump_runs) if has_visible_history else None,
            "flatOrUnknownRunsDatedBeforeRace": len(raw) - len(jump_runs) if has_visible_history else None,
            "historyState": "partial-visible" if has_visible_history else (
                "packed-not-decoded" if packed else "unverified"),
        })
    return {
        "box": "jra-jumps",
        "horseCount": len(rows),
        "horses": rows,
        "missingEvidenceHorses": sum(bool(row["missingFields"]) for row in rows),
        "historyPolicy": "keep-jumps-separate-from-flat;no-undated-or-same-day-runs",
        "researchFocus": ["jumpStarts", "jumpTrial", "jumpFlightQuality", "courseObstacles",
                          "jumpJockeyStats", "stamina", "flatAbilityAsContextOnly"],
        "note": "障害戦専用。平地成績を障害実績に混ぜず、飛越・障害適性・飛越経験の未取得を明示する。",
    }
