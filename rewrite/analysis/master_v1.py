"""ARVEXQ 18-section master forecast candidate (NOT production-calibrated).

Builds a reproducible full-field, pre-off research forecast.  Scoring
weights are user-specified ANALYTICAL priors, not fitted coefficients.
Missing facts are excluded from scoring and counted in coverage; market
odds never enter the ability score or the probabilities.

No promotion to production, purchase recommendations, or validated
expected-return estimates is made by this module.  To promote a model,
time-ordered out-of-sample races and sealed pre-off comparisons are required.
"""
from __future__ import annotations

from itertools import combinations
from math import exp, isfinite
from typing import Any

from rewrite.analysis.ability import LOWER_IS_BETTER, extract_features
from rewrite.analysis.pace import forecast_pace, style_profile
from rewrite.data.normalize import RaceRecord
from rewrite.safety.contracts import Segment
from rewrite.safety.probability import distribution, marginals, ticket_probability

VERSION = "arvexq-master-v1-18sections-candidate"
SCORE_WEIGHTS = {
    "ability": 24, "recent": 15, "course": 14, "pace": 15,
    "condition": 8, "training_state": 8, "jockey_stable": 6,
    "draw": 4, "weight_schedule": 6,
}
assert sum(SCORE_WEIGHTS.values()) == 100
CATEGORY_FEATURES = {
    # Different signals in the ability and recency boxes avoid reusing
    # finishing position in two independent 24+15 point allocations.
    "ability": ("speed", "class_recent", "class_drop"),
    "recent": ("form", "consistency", "top3_rate"),
    "course": ("distance", "track", "surface"),
    "condition": ("condition",),
    "jockey_stable": ("jockey",),
    "weight_schedule": ("weight_shift",),
}
# The following are DECLARED UNFITTED, segment-specific strength scales.
# They are not derived from a score percentage and must not be advertised
# as calibrated hit rates.
BETA_PRIORS = {
    Segment.JRA_FLAT: 2.5, Segment.NAR: 2.5,
    Segment.JUMPS: 2.0, Segment.DEBUT: 2.0,
}
SCENARIOS = ("slow", "normal", "fast")
MIN_COVERAGE_FOR_PROBABILITY = 0.40


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if isfinite(float(value)) else None


def _scale(values: dict[int, float], reverse: bool = False) -> dict[int, float]:
    """Within-race normalization; one observed horse gives no ranking evidence."""
    if len(values) < 2:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return {n: 0.5 for n in values}
    return {
        n: (1 - (x - lo) / (hi - lo) if reverse else (x - lo) / (hi - lo))
        for n, x in values.items()
    }


def _style(runner, mode: str, front_count: int) -> float | None:
    profile = style_profile(runner)
    if profile.start_ratio is None:
        return None
    # Position-based priors are NOT measured scenario frequencies.
    # Small adjustments only; they require separate ablation evidence.
    front = profile.start_ratio <= 0.35
    closing = profile.closing_gain if profile.closing_gain is not None else 0.0
    closing = max(-0.25, min(0.25, closing))
    if mode == "slow":
        return 0.5 + (0.07 if front else -0.02) - 0.12 * closing
    if mode == "fast":
        return 0.5 + 0.20 * closing - (0.07 if front and front_count >= 3 else 0.0)
    return 0.5 + 0.10 * closing + (0.02 if front_count == 1 and front else 0.0)


def _category_scores(race: RaceRecord, mode: str) -> tuple[dict[int, dict], dict[int, dict]]:
    active = race.active_runners
    features = {r.number: extract_features(race, r) for r in active}
    styles = {r.number: style_profile(r) for r in active}
    front_count = sum(
        s.start_ratio is not None and s.start_ratio <= 0.35
        for s in styles.values()
    )
    keys = {key for group in CATEGORY_FEATURES.values() for key in group}
    raw: dict[str, dict[int, float]] = {}
    for key in keys:
        raw[key] = {}
        for n, f in features.items():
            v = _finite_number(f.raw.get(key))
            if v is not None and f.evidence_counts.get(key, 0) > 0:
                raw[key][n] = v
    raw["pace"] = {
        r.number: score for r in active
        if (score := _style(r, mode, front_count)) is not None
    }
    scaled = {
        key: _scale(values, key in LOWER_IS_BETTER)
        for key, values in raw.items()
    }
    scores: dict[int, dict] = {}
    for r in active:
        n = r.number
        parts: dict[str, float | None] = {}
        for category in SCORE_WEIGHTS:
            if category == "pace":
                components = [scaled["pace"][n]] if n in scaled["pace"] else []
            else:
                components = [
                    scaled[key][n]
                    for key in CATEGORY_FEATURES.get(category, ())
                    if n in scaled[key]
                ]
            parts[category] = sum(components) / len(components) if components else None
        covered = sum(SCORE_WEIGHTS[k] for k, v in parts.items() if v is not None)
        score = (
            sum(SCORE_WEIGHTS[k] * v for k, v in parts.items() if v is not None)
            / covered * 100
            if covered else None
        )
        scores[n] = {
            "score": round(score, 1) if score is not None else None,
            "coverage": round(covered / 100, 3),
            "categoryScores": {
                k: round(v * SCORE_WEIGHTS[k], 2) if v is not None else None
                for k, v in parts.items()
            },
            "missingCategories": [k for k, v in parts.items() if v is None],
            "historyCount": len(r.past_runs),
        }
    return scores, features


def _scenario_distribution(scores: dict[int, dict], beta: float):
    if (len(scores) < 3 or any(
        row["score"] is None or row["coverage"] < MIN_COVERAGE_FOR_PROBABILITY
        for row in scores.values()
    )):
        return None
    mean = sum(row["score"] for row in scores.values()) / len(scores)
    strengths = {n: exp(beta * ((row["score"] - mean) / 100))
                 for n, row in scores.items()}
    outcomes = distribution(strengths)
    return outcomes, marginals(outcomes)


def _market_rank(race: RaceRecord) -> dict[int, int]:
    rows = []
    for r in race.active_runners:
        odds = _finite_number(r.win_odds.value)
        if odds is not None and odds > 1:
            rows.append((odds, r.number))
    return {n: i + 1 for i, (_, n) in enumerate(sorted(rows))}


def _ticket(kind: str, numbers: tuple[int, ...], outcomes: dict,
            place_slots: int) -> dict:
    p = ticket_probability(outcomes, kind, numbers, place_count=place_slots)
    return {
        "kind": kind, "horseNumbers": list(numbers), "points": 1,
        "probability": round(p, 4),
        "probabilityStatus": "unvalidated-prior",
        "quotedOdds": None, "expectedReturn": None,
        "purchaseEligible": False,
    }


def _strategies(ranked: list[int], top3: dict[int, float],
                outcomes: dict | None, market: dict[int, int],
                active_count: int) -> dict:
    if not outcomes:
        return {"hitFirst": [], "balanced": [], "outsider": [],
                "stakeFor1000Yen": {"hitFirst": 0, "balanced": 0, "outsider": 0},
                "decision": "見送り", "reason": "全頭の事前証拠が不足"}
    place_slots = 2 if active_count <= 7 else 3
    hit = (
        [_ticket("place", (max(top3, key=lambda n: (top3[n], -n)),),
                 outcomes, place_slots)]
        if active_count >= 5 else
        [_ticket("win", (ranked[0],), outcomes, place_slots)]
    )
    balanced = (
        [_ticket("wide", tuple(sorted(pair)), outcomes, place_slots)
         for pair in combinations(ranked[:3], 2)][:2]
        if active_count >= 5 else
        [_ticket("quinella", tuple(sorted(ranked[:2])), outcomes, place_slots)]
    )
    model_rank = {n: i + 1 for i, n in enumerate(ranked)}
    # A contrarian is only identified if observed odds actually rank
    # the same active runners; no guessed market rank is permitted.
    outsider_candidates = [
        n for n in ranked[2:] if n in market
        and market[n] - model_rank[n] >= 2
    ]
    outsider_candidates.sort(key=lambda n: (-top3[n], n))
    outsider = (
        [_ticket("wide", tuple(sorted((ranked[0], outsider_candidates[0]))),
                 outcomes, place_slots)]
        if outsider_candidates and active_count >= 5 else []
    )
    return {
        "hitFirst": hit, "balanced": balanced, "outsider": outsider,
        "stakeFor1000Yen": {"hitFirst": 0, "balanced": 0, "outsider": 0},
        "decision": "見送り",
        "reason": ("候補券種の結合確率は未校正。券種別の実オッズと"
                   "未使用レースでの確率校正が揃うまで購入推奨しない"),
    }


def forecast_master(race: RaceRecord) -> dict:
    """Full-field pre-off shadow forecast; never overrides frozen production picks."""
    active = race.active_runners
    if race.track.startswith("帯広"):
        raise ValueError("banei excluded")
    if len({r.number for r in race.runners}) != len(race.runners):
        raise ValueError("duplicate horse number")
    if len(active) < 3:
        return {
            "version": VERSION, "raceId": race.race_id,
            "status": "insufficient-active-roster", "rows": [],
            "decision": "見送り",
        }
    if race.segment not in BETA_PRIORS:
        raise ValueError("unrecognized segment")
    if race.segment is Segment.DEBUT:
        # Bloodline / training information is not normalized into the
        # current source; racing-history features cannot substitute it.
        allow_probabilities = False
    else:
        allow_probabilities = True
    scenario_data = {}
    for mode in SCENARIOS:
        scores, _ = _category_scores(race, mode)
        result = (_scenario_distribution(scores, BETA_PRIORS[race.segment])
                  if allow_probabilities else None)
        scenario_data[mode] = (scores, result)
    normal_scores, normal_result = scenario_data["normal"]
    status = "unvalidated-prior" if normal_result else "insufficient-evidence"
    probs = normal_result[1] if normal_result else {}
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    # Without usable probabilities: score-only ordering is permitted,
    # but no invented mark or zero-percent probability is issued.
    if not ranked:
        ranked = sorted(
            (r.number for r in active),
            key=lambda n: (
                normal_scores[n]["score"] is None,
                -(normal_scores[n]["score"] or 0),
                n,
            ),
        )
    marks = dict(zip(ranked[:5], "◎○▲△☆")) if normal_result else {}
    market = _market_rank(race)
    by_n = {r.number: r for r in race.runners}
    rows = []
    for n in ranked:
        item = normal_scores[n]
        seen = {
            mode: data[1][1].get(n) if data[1] else None
            for mode, data in scenario_data.items()
        }
        range_top3 = [
            value[2] for value in seen.values() if value is not None
        ]
        r = by_n[n]
        rows.append({
            "horseNumber": n, "name": r.name.value, "rank": len(rows) + 1,
            "mark": marks.get(n, ""),
            "score100": item["score"], "evidenceCoverage": item["coverage"],
            "categoryScores": item["categoryScores"],
            "missingCategories": item["missingCategories"],
            "historyCount": item["historyCount"],
            "winProbability": round(probs[n][0], 4) if n in probs else None,
            "top2Probability": round(probs[n][1], 4) if n in probs else None,
            "top3Probability": round(probs[n][2], 4) if n in probs else None,
            "top3ScenarioRange": (
                [round(min(range_top3), 4), round(max(range_top3), 4)]
                if range_top3 else None
            ),
            "marketRank": market.get(n),
            "marketRankStatus": "observed-odds-rank-unverified-source",
        })
    for r in race.runners:
        if r.scratched:
            rows.append({
                "horseNumber": r.number, "name": r.name.value, "rank": None,
                "mark": "", "score100": None, "status": "scratched",
                "winProbability": None, "top2Probability": None,
                "top3Probability": None,
            })
    outcomes = normal_result[0] if normal_result else None
    bets = _strategies(
        ranked, {n: probs[n][2] for n in probs}, outcomes, market, len(active)
    )
    pace = forecast_pace(race)
    # Actual 3-way scenario frequencies have not been calibrated;
    # never print a fabricated percentage or silently weight them 1/3.
    stages = {
        key: [n for n, _ in pace.stages[key].order]
        for key in ("start", "corner3", "corner4", "straight")
    }
    top3_leader = (
        max(probs, key=lambda n: (probs[n][2], -n)) if probs else None
    )
    coverage = min((row["evidenceCoverage"] for row in rows
                    if row.get("evidenceCoverage") is not None), default=0)
    trust = "C" if probs and coverage >= 0.65 else "D"
    return {
        "version": VERSION, "raceId": race.race_id, "date": race.date,
        "segment": race.segment.value, "source": race.source, "status": status,
        "scoring": {
            "weights": SCORE_WEIGHTS, "weightsStatus": "user-prior-unfitted",
            "normalization": "within-race-available-facts-only",
            "missingIsNotZero": True,
        },
        "probabilityModel": {
            "method": "Plackett-Luce-top3-permutation",
            "beta": BETA_PRIORS[race.segment],
            "status": status, "heldOutCalibration": False,
            "scenarioLikelihoods": {mode: None for mode in SCENARIOS},
            "scenarioWeightsFitted": False,
        },
        "rows": rows, "honmeiNumber": ranked[0] if probs else None,
        "top3AnchorNumber": top3_leader,
        "marketIsSeparateFromAbility": True,
        "pace": {
            "label": pace.pace_label, "frontNumbers": list(pace.front_runners),
            "stages": stages,
            "unknownNumbers": list(pace.unknown_runners),
            "scenarios": list(SCENARIOS),
        },
        "betCandidates": bets,
        "confidence": trust, "purchaseDecision": "見送り",
        "counterchecks": {
            "honmeiUpsetScenarios": [
                "想定と異なる前半ペース", "当日トラックバイアスの変化",
                "調教・体調・スタートに関する未取得情報",
            ],
            "unverifiedInputs": [
                "track-bias", "course-first-corner-distance",
                "training", "pedigree", "video-identity",
                "scenario-frequency", "joint-probability-calibration",
                "ticket-odds",
            ],
            "winnerAndPlaceAnchorMayDiffer": (
                ranked[0] != top3_leader if probs else None
            ),
        },
    }
