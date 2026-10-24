"""JRA debut-race evidence box: no invented past runs or bloodline ability."""
from __future__ import annotations

from typing import Any

_SOURCE_KEYS = {
    "sire": ("sire", "father"),
    "dam": ("dam", "mother"),
    "damSire": ("damSire", "broodmareSire", "mothersFather"),
    "trainer": ("trainer",),
    "jockey": ("jockey",),
    "workout": ("workoutTimes", "trainingTimes", "trainingRecords", "workouts"),
    "gateExam": ("gateExam", "gateTest", "startingGateTest"),
    "debutStats": ("trainerDebutStats", "jockeyDebutStats", "sireDebutStats"),
}


def _present(horse: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in horse and horse[key] is not None
               and horse[key] != "" and horse[key] != [] and horse[key] != {}
               for key in keys)


def build_debut_box(detail: dict[str, Any]) -> dict[str, Any]:
    """Report observed fields, never equate zero visible starts with proof."""
    rows = []
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict) or not horse.get("horseNumber") or horse.get("scratched"):
            continue
        observed = [key for key, aliases in _SOURCE_KEYS.items() if _present(horse, aliases)]
        missing = [key for key in _SOURCE_KEYS if key not in observed]
        history = horse.get("allPastRuns") or horse.get("recentRaces")
        rows.append({
            "horseNumber": int(horse["horseNumber"]),
            "name": str(horse.get("name") or ""),
            "observedFields": observed,
            "missingFields": missing,
            "visiblePriorStarts": len(history) if isinstance(history, list) else None,
            "firstStartConfirmed": False,  # Title alone does not verify every runner.
        })
    return {
        "box": "jra-debut",
        "horseCount": len(rows),
        "horses": rows,
        "missingEvidenceHorses": sum(bool(row["missingFields"]) for row in rows),
        "historyPolicy": "debut-has-no-performance-baseline;zero-visible-is-not-verified-zero",
        "researchFocus": ["pedigree", "workout", "gateExam", "trainerDebutStats", "jockeyDebutStats"],
        "note": "新馬戦専用。過去走欠損を能力ゼロとせず、調教・血統・初出走確認の実測が揃うまで確率の検証済み表示をしない。",
    }
