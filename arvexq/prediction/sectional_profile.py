"""Observed sectional evidence only; never infer measured gate reaction from corner order."""
from __future__ import annotations

from typing import Any

VERSION = "arvexq-sectional-evidence-v1"
EARLY = ("first3FSeconds", "early3FSeconds", "early3F", "first3F")
CRUISE = ("middle3FSeconds", "middle3F", "cruise3FSeconds")
# Both key spellings exist in stored records: the JRA公式 cell parser
# and app.py's inline result parser write last3FSeconds (capital F),
# while the netkeiba career builder, the NAR公式CSV reader and the
# legacy bridge write last3fSeconds / last3f (lowercase f). Until
# 2026-11-18 this tuple named only the capital-F variants, so every
# NAR run (and most JRA runs) read as unmeasured here even though the
# record carried the observed value.
LATE = ("last3FSeconds", "last3F", "closing3FSeconds",
        "last3fSeconds", "last3f", "last600Seconds", "last600")
PERCENTILE = ("last3FPercentile", "last3fPercentile", "last600Percentile")
RANKS = ("last3fRank", "last3FRank", "last600Rank", "上がり順位")


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
    past = sorted([row for row in past if isinstance(row, dict)],
                  key=lambda row: str(row.get("date") or row.get("raceDate") or ""), reverse=True)
    output = []
    for run in past:
        if not isinstance(run, dict):
            continue
        day = str(run.get("date") or run.get("raceDate") or "")
        if not day or not cutoff or day >= cutoff:
            continue
        early, middle, late = measured(run, EARLY), measured(run, CRUISE), measured(run, LATE)
        closing_rank = None
        for key in PERCENTILE:
            try:
                value = float(run.get(key))
                if 0 <= value <= 1:
                    closing_rank = value
                    break
            except (TypeError, ValueError):
                continue
        if closing_rank is None:
            # Reconstruct the same within-race percentile from the
            # published last-3F rank and field size (the transform
            # jra_sectional_evidence uses); never from raw seconds.
            rank = None
            for key in RANKS:
                try:
                    rank = float(run.get(key))
                    break
                except (TypeError, ValueError):
                    continue
            try:
                field = float(run.get("fieldSize"))
            except (TypeError, ValueError):
                field = None
            if (rank is not None and field is not None and field >= 2
                    and 1 <= rank <= field):
                closing_rank = 1.0 - (rank - 1.0) / (field - 1.0)
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
