"""Probability and marks layer: ability + pace -> Plackett-Luce.

Strength transform: s = exp(beta * (score - race_mean_score)), with
beta a declared prior constant (DEFAULT_BETA) until the calibration
step fits it on a time-ordered training slice. Pace fit applies a
small, fully recorded multiplicative adjustment. Probabilities from
this layer are labelled ``uncalibrated-prior`` and must never be
presented as verified until held-out calibration evidence exists.

Marks are mechanical: ◎○▲△ by win probability (ties broken by top-3
probability, then horse number), ☆ is the strongest "place-type"
runner outside the top four — highest top-3 probability among those
whose win probability is below the race's marked four — falling back
to the fifth-ranked runner when no such outsider exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Optional

from ..data.normalize import RaceRecord
from ..safety.probability import distribution, marginals
from .ability import AbilityResult, analyze_race
from .pace import PaceForecast, forecast_pace, style_profile

DEFAULT_BETA = 4.0
# Every starter can win. A runner the ability layer could not score
# (no usable past-run evidence) is not assigned zero probability: it
# enters the distribution at a floor strength relative to the weakest
# scored runner. The floor is a declared prior constant, and floored
# runners keep the visible status "unscored-floor-strength".
FLOOR_FRACTION = 0.10
PACE_FRONT_CROWD_PENALTY = 0.92
PACE_CLOSER_BOOST = 1.08
PACE_LONE_FRONT_BOOST = 1.08
PROBABILITY_STATUS = "uncalibrated-prior"


@dataclass(frozen=True)
class RunnerForecast:
    number: int
    name: Optional[str]
    ability_score: Optional[float]
    strength: Optional[float]
    pace_adjustment: float
    pace_reasons: tuple
    p_win: Optional[float]
    p_top2: Optional[float]
    p_top3: Optional[float]
    mark: str
    status: str


@dataclass(frozen=True)
class RaceForecast:
    race_id: str
    beta: float
    probability_status: str
    runners: tuple
    status: str


def _pace_adjustments(race: RaceRecord, pace: PaceForecast) -> dict[int, tuple[float, tuple]]:
    adjustments: dict[int, tuple[float, tuple]] = {}
    profiles = {p.number: p for p in (style_profile(r) for r in race.active_runners)}
    front = set(pace.front_runners)
    crowded = len(front) >= 3
    lone = len(front) == 1
    for number, profile in profiles.items():
        factor = 1.0
        reasons: list[str] = []
        closing = profile.closing_gain or 0.0
        if crowded and number in front:
            factor *= PACE_FRONT_CROWD_PENALTY
            reasons.append("front-crowded-penalty")
        if crowded and closing >= 0.05:
            factor *= PACE_CLOSER_BOOST
            reasons.append("closer-boost-fast-pace")
        if lone and number in front:
            factor *= PACE_LONE_FRONT_BOOST
            reasons.append("lone-front-boost")
        adjustments[number] = (factor, tuple(reasons))
    return adjustments


def _assign_marks(ranked: list[int], probs: dict[int, tuple]) -> dict[int, str]:
    marks: dict[int, str] = {}
    for index, symbol in enumerate(("◎", "○", "▲", "△")):
        if index < len(ranked):
            marks[ranked[index]] = symbol
    rest = ranked[4:]
    if rest:
        star = max(rest, key=lambda n: (probs[n][2], probs[n][0], -n))
        marks[star] = "☆"
    return marks


def forecast_race(race: RaceRecord, beta: float = DEFAULT_BETA) -> RaceForecast:
    ability = analyze_race(race)
    pace = forecast_pace(race)
    adjustments = _pace_adjustments(race, pace)
    scored = [a for a in ability if a.score is not None]
    if len(scored) < 3:
        runners = tuple(
            RunnerForecast(
                number=a.number, name=a.name, ability_score=a.score,
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="insufficient-scored-runners",
            )
            for a in ability
        )
        return RaceForecast(race.race_id, beta, PROBABILITY_STATUS, runners,
                            "insufficient-scored-runners")
    mean_score = sum(a.score for a in scored) / len(scored)
    strengths: dict[int, float] = {}
    for a in scored:
        factor, _ = adjustments.get(a.number, (1.0, ()))
        strengths[a.number] = exp(beta * (a.score - mean_score)) * factor
    floor = FLOOR_FRACTION * min(strengths.values())
    floored = {
        a.number for a in ability
        if a.score is None and a.number in {r.number for r in race.active_runners}
    }
    for number in floored:
        strengths[number] = floor
    outcomes = distribution(strengths)
    probs = marginals(outcomes)
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranked, probs)
    by_number = {a.number: a for a in ability}
    runners = []
    for number in sorted(by_number):
        a = by_number[number]
        if number in probs:
            factor, reasons = adjustments.get(number, (1.0, ()))
            runners.append(RunnerForecast(
                number=number, name=a.name, ability_score=a.score,
                strength=round(strengths[number], 6), pace_adjustment=factor,
                pace_reasons=reasons,
                p_win=round(probs[number][0], 4), p_top2=round(probs[number][1], 4),
                p_top3=round(probs[number][2], 4), mark=marks.get(number, ""),
                status=("unscored-floor-strength" if number in floored
                        else "forecast-uncalibrated"),
            ))
        else:
            runners.append(RunnerForecast(
                number=number, name=a.name, ability_score=a.score,
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status=a.status,
            ))
    return RaceForecast(race.race_id, beta, PROBABILITY_STATUS, tuple(runners), "ok")
