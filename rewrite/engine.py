"""ARVEXQ replacement prediction core. Independent of all legacy engines.

Inputs are acquired pre-off facts only. No implied odds, probabilities or
historical results are invented when evidence is missing.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite
from typing import Any

MARKS = ("◎", "○", "▲", "△", "☆")

@dataclass(frozen=True)
class Horse:
    number: int
    name: str
    history: tuple[dict[str, Any], ...]
    win_odds: float | None = None
    scratched: bool = False

def _valid_history(row: dict[str, Any], cutoff: str) -> bool:
    date = str(row.get("date") or "")
    finish = row.get("finish")
    return bool(date and date < cutoff and isinstance(finish, int)
                and finish > 0 and 1 <= int(row.get("fieldSize") or 0) <= 30
                and finish <= int(row["fieldSize"]))

def normalize_race(payload: dict[str, Any]) -> tuple[str, str, list[Horse]]:
    if not isinstance(payload, dict): raise ValueError("race must be an object")
    date = str(payload.get("date") or "")
    datetime.strptime(date, "%Y-%m-%d")
    circuit = str(payload.get("circuit") or "")
    if circuit not in ("中央", "地方"): raise ValueError("invalid circuit")
    if str(payload.get("track") or "") in ("帯広", "帯広ば"): raise ValueError("banei excluded")
    horses = []
    seen = set()
    for h in payload.get("horses") or []:
        number = h.get("horseNumber")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1 or number in seen:
            raise ValueError("invalid or duplicate horse number")
        seen.add(number)
        name = str(h.get("name") or "").strip()
        if not name: raise ValueError("missing horse name")
        raw_odds = h.get("winOdds")
        odds = float(raw_odds) if raw_odds is not None else None
        if odds is not None and (not isfinite(odds) or odds < 1): odds = None
        histories = tuple(x for x in h.get("recentRaces", []) if isinstance(x, dict) and _valid_history(x, date))
        horses.append(Horse(number, name, histories, odds, bool(h.get("scratched") or h.get("withdrawn"))))
    if len(horses) < 3: raise ValueError("incomplete roster")
    return date, circuit, horses

def ability(horse: Horse, circuit: str, race: dict[str, Any]) -> tuple[float, int]:
    # Ranking signal only. Calibration is necessary before probabilities or wagers.
    rows = horse.history[:8]
    if not rows: return 0.0, 0
    score, weight = 0.0, 0.0
    for index, past in enumerate(rows):
        field, finish = int(past["fieldSize"]), int(past["finish"])
        rank_strength = (field - finish) / max(1, field - 1)
        distance = race.get("distance")
        match = 1.0 if distance and past.get("distance") == distance else 0.0
        track_match = 1.0 if past.get("track") == race.get("track") else 0.0
        surface_match = 1.0 if past.get("surface") == race.get("surface") else 0.0
        relevance = 1 / (1 + index * .2)
        # Central and local leagues are never pooled into a single fitted probability.
        circuit_weight = 1.0 if circuit == "中央" else .95
        score += relevance * (rank_strength + .12 * match + .08 * track_match
                              + .08 * surface_match) * circuit_weight
        weight += relevance
    return score / weight, len(rows)

def pace_scenarios(horses: list[Horse]) -> dict[str, list[dict[str, Any]]]:
    # Positional classifications are observations, not fictitious timing estimates.
    profiles = []
    for h in horses:
        first_corners = []
        for past in h.history:
            corners = past.get("cornerPositions")
            if isinstance(corners, list) and corners and isinstance(corners[0], int):
                first_corners.append(corners[0] / max(1, past["fieldSize"]))
        position = sum(first_corners) / len(first_corners) if first_corners else None
        profiles.append({"horseNumber": h.number, "positionRatio": round(position, 3)
                         if position is not None else None,
                         "basisCount": len(first_corners)})
    def order(mode: str) -> list[dict[str, Any]]:
        entries = [dict(p) for p in profiles]
        entries.sort(key=lambda p: ((p["positionRatio"] is None),
                     -(p["positionRatio"] or 0) if mode == "fast" else (p["positionRatio"] or 0),
                     p["horseNumber"]))
        return entries
    return {"start": order("normal"), "thirdCorner": order("normal"),
            "fourthCorner": order("normal"), "straight": order("fast"),
            "alternativeFastPace": order("fast")}

def forecast(payload: dict[str, Any], calibration: dict[str, Any] | None = None) -> dict[str, Any]:
    date, circuit, horses = normalize_race(payload)
    active = [h for h in horses if not h.scratched]
    if len(active) < 3: raise ValueError("not enough active horses")
    metrics = [(h, *ability(h, circuit, payload)) for h in active]
    metrics.sort(key=lambda x: (-x[1], -x[2], x[0].number))
    valid = all(n >= 1 for _, _, n in metrics)
    rows = [{"horseNumber": h.number, "name": h.name, "evidenceCount": n,
             "abilityScore": round(score, 4) if n else None,
             "mark": MARKS[i] if valid and i < len(MARKS) else "",
             "winProbability": None, "top3Probability": None}
            for i, (h, score, n) in enumerate(metrics)]
    # Future out-of-sample probability calibration must be a separately verified artifact.
    # No fake win rates or expected-value bets.
    return {"version": "arvexq-rewrite-v1", "raceId": payload.get("id"),
            "date": date, "circuit": circuit,
            "status": "ranked-unvalidated" if valid else "insufficient-horse-evidence",
            "rows": rows, "pace": pace_scenarios(active),
            "calibrationStatus": "not-verified", "bets": [],
            "betDecision": "見送り", "missingEvidence": [h.number for h, _, n in metrics if n == 0],
            "videoStatus": "not-applied-unverified"}
