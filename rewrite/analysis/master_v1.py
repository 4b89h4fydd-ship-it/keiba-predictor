"""ARVEXQ master 18-part specification: evidence-led experimental forecast.

This is a SHADOW candidate, not a validated replacement for v9b. The nine
100-point categories are *prior* allocations, not learned coefficients.
Unobserved facts stay unavailable; no training, video, gate, or bloodline
signal is fabricated. Market odds never enter the 100-point ability score.
"""
from __future__ import annotations

from math import exp, fsum, isfinite
from typing import Optional

from .ability import analyze_race
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .pace import forecast_pace
from ..data.normalize import RaceRecord
from ..safety.probability import distribution, marginals

MODEL_VERSION = "master-18-factor-shadow-v1"
PROBABILITY_STATUS = "experimental-uncalibrated"
# The user-supplied 100-point category allocations are priors only.
CATEGORY_POINTS = {
    "ability": 24,
    "recent": 15,
    "course_distance": 14,
    "pace_robustness": 15,
    "track_condition": 8,
    "training_condition": 8,
    "jockey_trainer": 6,
    "gate": 4,
    "weight_rotation": 6,
}
assert sum(CATEGORY_POINTS.values()) == 100

# Each observed category is a weighted mean of *distinct* features where
# possible. Form is assigned to recent; historical top3_rate is intentionally
# omitted because it duplicates form. All normalized values are 0..1.
FEATURES = {
    "ability": {"speed": 0.55, "class_recent": 0.20, "class_drop": 0.25},
    "recent": {"form": 0.75, "consistency": 0.25},
    "course_distance": {"distance": 0.55, "track": 0.30, "surface": 0.15},
    "track_condition": {"condition": 1.0},
    "jockey_trainer": {"jockey": 1.0},
    "weight_rotation": {"weight_shift": 0.50, "rest": 0.50},
}
# Perturbation strength is a declared, unfitted research hyperparameter.
LOG_STRENGTH_GAIN = 1.0


def _category_value(normalized: dict, features: dict[str, float]) -> Optional[float]:
    observed = [(normalized[k], weight) for k, weight in features.items()
                if normalized.get(k) is not None and weight > 0]
    if not observed:
        return None
    return sum(value * weight for value, weight in observed) / sum(
        weight for _, weight in observed)


def _pace_robustness(pace, number: int) -> Optional[float]:
    """Reward being competitive across all three scenarios, not just one."""
    merits = []
    for scenario in ("slow", "normal", "fast"):
        order = [n for n, _ in pace.scenarios[scenario]["straight_order"].order]
        if number not in order or len(order) < 2:
            return None
        merits.append(1.0 - order.index(number) / (len(order) - 1))
    return 0.5 * sum(merits) / len(merits) + 0.5 * min(merits)


def _market_probs(race: RaceRecord) -> Optional[dict[int, float]]:
    active = race.active_runners
    odds = {}
    for runner in active:
        value = runner.win_odds.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if not isfinite(value) or value <= 1.0:
            return None
        odds[runner.number] = float(value)
    total = fsum(1.0 / value for value in odds.values())
    return {n: (1.0 / odds[n]) / total for n in odds} if total else None


def master_candidate(race: RaceRecord, incumbent: RaceForecast) -> tuple[RaceForecast, dict]:
    """Evaluate all active horses, then compute a **shadow** PL distribution.

    The incumbent strengths anchor the experimental scores. No published
    mark, frozen receipt, or historical record is mutated by this function.
    Caller must not advertise the returned probabilities as calibrated.
    """
    if incumbent.race_id != race.race_id:
        raise ValueError("race identity mismatch")
    ability = {a.number: a for a in analyze_race(race)}
    pace = forecast_pace(race)
    market = _market_probs(race)
    rows = []
    for runner in race.active_runners:
        number = runner.number
        a = ability[number]
        categories = {}
        for category, points in CATEGORY_POINTS.items():
            if category == "pace_robustness":
                value = _pace_robustness(pace, number)
            else:
                value = _category_value(a.normalized, FEATURES[category]) if category in FEATURES else None
            categories[category] = {
                "maximum": points,
                "earned": round(points * value, 2) if value is not None else None,
                "status": "observed-derived" if value is not None else "unavailable",
            }
        available = sum(CATEGORY_POINTS[k] for k, v in categories.items()
                        if v["earned"] is not None)
        earned = sum(v["earned"] for v in categories.values() if v["earned"] is not None)
        # A full 100-point *comparable estimate*, not a claim that all
        # nine categories were measured. Coverage is mandatory alongside it.
        score = 100.0 * earned / available if available >= 35 else None
        rows.append({
            "horseNumber": number,
            "name": runner.name.value if runner.name.present else None,
            "score100": round(score, 2) if score is not None else None,
            "observedPoints": round(earned, 2),
            "coveragePoints": available,
            "evidenceRuns": a.features.evidence_runs,
            "categories": categories,
            "missingCategories": [k for k, v in categories.items() if v["earned"] is None],
        })
    by_number = {r["horseNumber"]: r for r in rows}
    if incumbent.status != "ok":
        return incumbent, {
            "version": MODEL_VERSION, "status": "insufficient-incumbent",
            "probabilityStatus": PROBABILITY_STATUS, "runners": rows,
            "pace": {"label": pace.pace_label, "unknown": list(pace.unknown_runners)},
            "marketStatus": "complete" if market is not None else "unavailable",
        }
    active = {r.number for r in incumbent.runners if r.strength is not None
              and r.strength > 0}
    if active != set(by_number) or len(active) < 3:
        raise ValueError("incumbent roster differs from active race")
    usable = [r["score100"] for r in rows if r["score100"] is not None]
    if len(usable) < 3:
        return incumbent, {
            "version": MODEL_VERSION, "status": "insufficient-master-evidence",
            "probabilityStatus": PROBABILITY_STATUS, "runners": rows,
            "pace": {"label": pace.pace_label, "unknown": list(pace.unknown_runners)},
            "marketStatus": "complete" if market is not None else "unavailable",
        }
    center = sum(usable) / len(usable)
    strengths = {}
    for r in incumbent.runners:
        row = by_number[r.number]
        factor = (exp(LOG_STRENGTH_GAIN * (row["score100"] - center) / 100.0)
                  if row["score100"] is not None else 1.0)
        strengths[r.number] = r.strength * factor
    probs = marginals(distribution(strengths))
    ranking = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranking, probs)
    new_runners = []
    for r in incumbent.runners:
        p = probs[r.number]
        new_runners.append(RunnerForecast(
            number=r.number, name=r.name, ability_score=r.ability_score,
            strength=strengths[r.number], pace_adjustment=r.pace_adjustment,
            pace_reasons=r.pace_reasons, p_win=p[0], p_top2=p[1],
            p_top3=p[2], mark=marks.get(r.number, ""),
            status="master-experimental" if by_number[r.number]["score100"] is not None
                   else "master-evidence-insufficient",
        ))
    candidate = RaceForecast(
        race.race_id, incumbent.beta, PROBABILITY_STATUS, tuple(new_runners), "ok")
    market_order = sorted(market, key=lambda n: (-market[n], n)) if market else []
    model_rank = {n: i + 1 for i, n in enumerate(ranking)}
    for row in rows:
        n = row["horseNumber"]
        row["mark"] = marks.get(n, "")
        row["pWin"] = round(probs[n][0], 4)
        row["pTop2"] = round(probs[n][1], 4)
        row["pTop3"] = round(probs[n][2], 4)
        row["marketRank"] = market_order.index(n) + 1 if market else None
        row["modelRank"] = model_rank[n]
        row["marketImpliedWin"] = round(market[n], 4) if market else None
        # These are research flags, never evidence of actual mispricing.
        row["popularRisk"] = (
            "C-candidate" if row["marketRank"] is not None
            and row["marketRank"] <= 3 and row["modelRank"] >= 5
            else "B-candidate" if market and row["marketRank"] <= 3
            and probs[n][0] < 0.75 * market[n]
            else "A-candidate" if market and row["marketRank"] <= 3
            else "not-assessed"
        )
        row["valueHypothesis"] = bool(market and probs[n][0] > 1.25 * market[n])
    leader = ranking[0]
    place_leader = max(probs, key=lambda n: (probs[n][2], -n))
    coverage = sum(r["coveragePoints"] for r in rows) / len(rows)
    # Only an evidence-quality label; never an observed hit-rate claim.
    confidence = ("B" if coverage >= 75 and not pace.unknown_runners
                  else "C" if coverage >= 50 else "D")
    scenario_order = {
        k: [n for n, _ in pace.scenarios[k]["straight_order"].order]
        for k in ("slow", "normal", "fast")
    }
    return candidate, {
        "version": MODEL_VERSION, "status": "shadow-candidate",
        "probabilityStatus": PROBABILITY_STATUS,
        "scoreStatus": "unfitted-100-point-prior",
        "runners": rows,
        "pace": {
            "label": pace.pace_label, "frontRunners": list(pace.front_runners),
            "unknown": list(pace.unknown_runners),
            "scenarioOrder": scenario_order,
            "scenarioProbabilities": None,
        },
        "marketStatus": "complete" if market is not None else "unavailable",
        "mostLikelyWinner": leader,
        "mostLikelyTop3": place_leader,
        "twoHeadHedge": sorted(probs, key=lambda n: (-probs[n][2], n))[:2],
        "evidenceConfidence": confidence,
        "validated": False,
        "notes": ["No paid or inaccessible training/video/bloodline data invented",
                  "Candidate must beat v9b on sealed forward races before adoption"],
    }
