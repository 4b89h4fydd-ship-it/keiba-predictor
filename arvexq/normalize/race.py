from __future__ import annotations

from copy import deepcopy
from typing import Any

from arvexq.core.runner_status import normalize_runner_status


def _number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        f = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def normalize_horse(horse: dict[str, Any]) -> dict[str, Any]:
    h = deepcopy(horse)
    h["status"] = normalize_runner_status(
        h.get("status"),
        scratched=bool(h.get("scratched")),
        withdrawn=bool(h.get("withdrawn")),
    )
    for key in ("horseNumber", "frameNumber", "age", "bodyWeight", "bodyWeightChange", "carriedWeight", "weight", "odds", "popularity"):
        if key in h:
            value = _number(h.get(key))
            if value is not None:
                h[key] = value
    runs = h.get("allPastRuns") or h.get("recentRaces") or []
    normalized_runs: list[dict[str, Any]] = []
    for raw in runs:
        if not isinstance(raw, dict):
            continue
        run = deepcopy(raw)
        for key in ("finish", "fieldSize", "distance", "timeSeconds", "speedIndex", "levelScore", "opponentLevel", "racePrize1"):
            if key in run:
                value = _number(run.get(key))
                if value is not None:
                    run[key] = value
        normalized_runs.append(run)
    h["recentRaces"] = normalized_runs[:5]
    if "allPastRuns" in h:
        h["allPastRuns"] = normalized_runs
    return h


def normalize_race(detail: dict[str, Any]) -> dict[str, Any]:
    race = deepcopy(detail)
    if "distance" in race:
        value = _number(race.get("distance"))
        if value is not None:
            race["distance"] = value
    race["horses"] = [normalize_horse(h) for h in (race.get("horses") or []) if isinstance(h, dict)]
    return race
