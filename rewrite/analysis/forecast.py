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

Debut lane (2026-11-28, user-directed): a first-starters-only
race has no past-run evidence, so the ability layer scores nobody
and forecast_race can only answer "insufficient-scored-runners".
forecast_debut_market below supplies the segment's declared prior
instead — the market itself, from the win odds observed at publish
time — so the collected materials (training grades, press marks,
comments) can be layered onto it by the materials adjustment
exactly as on the other lanes. The probabilities stay labelled
"uncalibrated-prior": the market is a prior here, not a fitted
model, and no ability claim is made for any runner.

Five marks only (2026-11-27, user-directed; supersedes the
2026-11-21 extended marks 注/穴/伏 at win-probability ranks 6-8).
The extended marks made the published ticket selection hard to
read, and a same-day re-measurement on the issued vectors of
2026-11-24..26 (117-118 races) showed no selection rule built
from the issued numbers picks a better five: ranking by top-3
probability or by the ability score captured FEWER podium
finishers (68.7-72.3%) than the plain win-probability top five
(72.4%, full-podium capture 35.9%). The five marks are therefore
exactly the win-probability top five under the assignment above;
improving WHICH five is a probability-quality question, not a
selection-rule question.
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


def forecast_race(
    race: RaceRecord,
    beta: float = DEFAULT_BETA,
    weights: dict | None = None,
) -> RaceForecast:
    ability = analyze_race(race, weights=weights)
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


# Status of a debut race whose market base is not yet usable: the
# publish lane defers on it (the same "wait for the input, then
# publish" pattern as the v8-extras deferral and the blend
# upgrade), so a debut race is never first-published on a partial
# market and never falls back to an ability vector that does not
# exist for the segment.
DEBUT_MARKET_INCOMPLETE = "debut-market-incomplete"
# Runner status on the debut lane's base vector: the runner's
# probability IS the market's, before any materials term moves it.
DEBUT_RUNNER_STATUS = "market-prior"


def forecast_debut_market(
    race: RaceRecord,
    win_odds: dict | None,
    beta: float = DEFAULT_BETA,
) -> RaceForecast:
    """Market-base forecast for a debut (first-starters-only) race.

    The base vector is the market-implied win probability of every
    active runner: inverse win odds, normalised so the overround
    is distributed proportionally — the same construction
    shadow_v9.market_probs uses for the v9b blend (kept local:
    shadow_v9 imports this module). The probabilities are carried
    as Plackett-Luce strengths (win marginal = strength / total,
    and the strengths already sum to 1), so the materials
    adjustment, the marks and the tickets downstream consume
    exactly the shape they consume on every other lane.

    The base is used only when the market is COMPLETE: every
    active runner must carry a real win odd (> 1.0) in
    ``win_odds``. Partial coverage returns a forecast with status
    DEBUT_MARKET_INCOMPLETE and no probabilities at all — odds are
    never imputed, and no runner is ever assigned a share of
    another runner's price. A field of fewer than three active
    runners is likewise incomplete (no Plackett-Luce vector, no
    five marks).

    Join keys are the race card's own horse numbers — the runners
    of the normalised race record itself. The v8 extras are never
    read here: their debut entries carry no ability evidence for
    the segment, and their horse-number keys are known to drift
    from the card in this segment.

    Every active runner keeps ability_score None and the status
    "market-prior": the lane makes no ability claim, and a runner
    no materials term covers keeps exactly her market probability
    (the materials adjustment only shifts runners a term actually
    covers). Scratched runners carry no probability.
    """
    active = race.active_runners
    numbers = [r.number for r in active]
    odds = win_odds or {}
    usable = len(numbers) >= 3 and all(
        isinstance(odds.get(n), (int, float))
        and not isinstance(odds.get(n), bool)
        and odds[n] > 1.0
        for n in numbers
    )
    if not usable:
        runners = tuple(
            RunnerForecast(
                number=r.number,
                name=r.name.value if r.name.present else None,
                ability_score=None, strength=None,
                pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status=DEBUT_MARKET_INCOMPLETE,
            )
            for r in sorted(race.runners, key=lambda r: r.number)
        )
        return RaceForecast(race.race_id, beta, PROBABILITY_STATUS,
                            runners, DEBUT_MARKET_INCOMPLETE)
    inverse = {n: 1.0 / float(odds[n]) for n in numbers}
    total = sum(inverse.values())
    strengths = {n: v / total for n, v in inverse.items()}
    outcomes = distribution(strengths)
    probs = marginals(outcomes)
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranked, probs)
    active_numbers = set(numbers)
    runners = []
    for r in sorted(race.runners, key=lambda r: r.number):
        name = r.name.value if r.name.present else None
        if r.number in active_numbers:
            runners.append(RunnerForecast(
                number=r.number, name=name, ability_score=None,
                strength=round(strengths[r.number], 6),
                pace_adjustment=1.0, pace_reasons=(),
                p_win=round(probs[r.number][0], 4),
                p_top2=round(probs[r.number][1], 4),
                p_top3=round(probs[r.number][2], 4),
                mark=marks.get(r.number, ""),
                status=DEBUT_RUNNER_STATUS,
            ))
        else:
            runners.append(RunnerForecast(
                number=r.number, name=name, ability_score=None,
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="scratched",
            ))
    return RaceForecast(race.race_id, beta, PROBABILITY_STATUS,
                        tuple(runners), "ok")
