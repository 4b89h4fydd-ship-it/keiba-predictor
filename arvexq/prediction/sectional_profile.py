"""Observed sectional evidence only; never infer measured gate reaction from corner order."""
from __future__ import annotations

from typing import Any

VERSION = "arvexq-sectional-evidence-v1"
EARLY = ("first3FSeconds", "early3FSeconds", "early3F", "first3F")
CRUISE = ("middle3FSeconds", "middle3F", "cruise3FSeconds")
LATE = ("last3FSeconds", "last3F", "closing3FSeconds")


def measured(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        try:
            value = float(row.get(key))
            if 8.0 <= value <= 90.0:
                return round(value, 2)
        except (TypeError, ValueError):
            pass
    return None


def profile(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    cutoff = str(race.get("date") or "")
    past = horse.get("allPastRuns") or horse.get("recentRaces") or []
    output = []
    for run in past:
        if not isinstance(run, dict):
            continue
        day = str(run.get("date") or run.get("raceDate") or "")
        if not day or not cutoff or day >= cutoff:
            continue
        early, middle, late = measured(run, EARLY), measured(run, CRUISE), measured(run, LATE)
        try:
            closing_rank = float(run.get("last3FPercentile"))
            closing_rank = closing_rank if 0 <= closing_rank <= 1 else None
        except (TypeError, ValueError):
            closing_rank = None
        output.append({
            "date": day, "distance": run.get("distance"),
            "early3FSeconds": early, "middle3FSeconds": middle,
            "late3FSeconds": late, "last3FWithinRacePercentile": closing_rank,
            "earlyCornerPosition": (run.get("cornerPositions") or [None])[0]
              if isinstance(run.get("cornerPositions"), (list, tuple)) and run.get("cornerPositions") else None,
        })
        if len(output) >= 5:
            break
    return {
        "version": VERSION, "runs": output,
        "measuredEarly": sum(z["early3FSeconds"] is not None for z in output),
        "measuredMiddle": sum(z["middle3FSeconds"] is not None for z in output),
        "measuredLate": sum(z["late3FSeconds"] is not None for z in output),
        "note": "初角順位は位置取りでありテン3F実測値・ゲート反応時間ではありません。異距離の秒数を単純比較しません。",
    }
