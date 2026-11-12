"""Research-only F1 challenger: evidence-decay shrinkage for the v8
ability score. NOT imported by any production path.

Audit finding F1 (2026-11-11 code audit): ``forecast_race_v8`` scores a
horse by renormalizing the segment weights over whichever features
happen to be available (minimum 3). A horse with a single career start
can therefore take the race maximum on form / top3_rate / rest, score
1.0 and be marked ◎ at a 52.5% win probability, outranking horses with
eight starts of full evidence. Evidence volume never damps the score.

This challenger keeps the production pipeline byte-identical except
for one step: after the raw renormalized scores are computed (exactly
as production does), each scored horse's score is shrunk toward the
race's scored-field mean by a reliability factor

    r = (n / (n + k)) * coverage ** coverage_power

where ``n`` is the horse's evidence run count (``evidence_runs`` from
``extract_features``, capped at 8 by the extractor) and ``coverage``
is the share of the segment's total fitted weight carried by the
features actually available for that horse. ``k`` is a prior-strength
constant: a horse needs on the order of ``k`` starts before its raw
score is trusted at face value. This is the standard empirical-Bayes /
James-Stein style shrinkage toward the group mean, applied on the
score scale the downstream strength transform already centers on.

Candidate configurations are deliberately few and fixed in advance
(no per-dataset tuning):

- ``runs-k2``:  k=2, coverage_power=0  (run-count shrinkage only)
- ``runs-k4``:  k=4, coverage_power=0
- ``cov-k2``:   k=2, coverage_power=1  (runs x weight coverage)
- ``cov-k4``:   k=4, coverage_power=1

The function below is a verbatim copy of
``rewrite.analysis.shadow_v8.forecast_race_v8`` with the shrinkage
block inserted where marked (``# --- F1 challenger change ---``).
Keeping the copy explicit makes the single difference auditable by
diff; nothing here mutates the production module.
"""
from __future__ import annotations

from math import exp
from typing import Optional

from rewrite.analysis.ability import _minmax, extract_features
from rewrite.analysis.forecast import (
    FLOOR_FRACTION,
    PROBABILITY_STATUS,
    RaceForecast,
    RunnerForecast,
    _assign_marks,
    _pace_adjustments,
)
from rewrite.analysis.pace import forecast_pace
from rewrite.analysis.shadow_v8 import (
    BETAS,
    EXTRA_FEATURES,
    LOWER_IS_BETTER_V8,
    WEIGHTS,
)
from rewrite.data.normalize import RaceRecord
from rewrite.safety.contracts import Segment
from rewrite.safety.probability import distribution, marginals

CANDIDATES: dict[str, dict[str, float]] = {
    "runs-k2": {"k": 2.0, "coverage_power": 0.0},
    "runs-k4": {"k": 4.0, "coverage_power": 0.0},
    "cov-k2": {"k": 2.0, "coverage_power": 1.0},
    "cov-k4": {"k": 4.0, "coverage_power": 1.0},
}


def reliability(evidence_runs: int, coverage: float, *,
                k: float, coverage_power: float) -> float:
    """Shrinkage factor in [0, 1]: 1 = trust the raw score fully."""
    if k <= 0:
        raise ValueError("k must be positive")
    run_factor = evidence_runs / (evidence_runs + k)
    return run_factor * (coverage ** coverage_power)


def forecast_race_v8_decay(
    race: RaceRecord,
    extras: Optional[dict[int, dict[str, float]]] = None,
    *,
    k: float = 4.0,
    coverage_power: float = 1.0,
) -> RaceForecast:
    """forecast_race_v8 with evidence-decay shrinkage on the scores.

    Identical to production except the marked block: raw scores are
    shrunk toward the scored-field mean by ``reliability`` before the
    strength transform. Unscored / floor handling is unchanged.
    """
    segment = race.segment.value
    weights = WEIGHTS[segment]
    beta = BETAS[segment]
    total_weight_all = sum(weights.values())
    active = list(race.active_runners)
    feats = {}
    for r in active:
        feat = extract_features(race, r)
        feats[r.number] = feat
    for number, extra in (extras or {}).items():
        if number not in feats:
            continue
        for key in EXTRA_FEATURES:
            value = extra.get(key)
            if value is not None:
                feats[number].raw[key] = value
                feats[number].evidence_counts[key] = 1
    normalized: dict[str, dict[int, float]] = {}
    for feature in weights:
        present = {
            n: feats[n].raw[feature]
            for n in feats if feats[n].raw.get(feature) is not None
        }
        normalized[feature] = _minmax(present, feature in LOWER_IS_BETTER_V8)
    pace = forecast_pace(race)
    adjustments = _pace_adjustments(race, pace)
    scores: dict[int, float] = {}
    coverage: dict[int, float] = {}
    for number, feat in feats.items():
        if race.segment is Segment.DEBUT or feat.evidence_runs == 0:
            continue
        available = {
            k_: normalized[k_][number]
            for k_ in weights if number in normalized.get(k_, {})
        }
        if len(available) < 3:
            continue
        total_w = sum(weights[k_] for k_ in available)
        scores[number] = round(
            sum(available[k_] * weights[k_] for k_ in available) / total_w, 4)
        coverage[number] = total_w / total_weight_all
    names = {r.number: (r.name.value if r.name.present else None)
             for r in active}
    if len(scores) < 3:
        runners = tuple(
            RunnerForecast(
                number=n, name=names[n], ability_score=scores.get(n),
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="insufficient-scored-runners",
            )
            for n in sorted(feats)
        )
        return RaceForecast(race.race_id, beta, PROBABILITY_STATUS,
                            runners, "insufficient-scored-runners")
    # --- F1 challenger change: shrink raw scores toward the
    # scored-field mean by evidence reliability before strengths. ---
    raw_mean = sum(scores.values()) / len(scores)
    scores = {
        n: round(raw_mean + reliability(
            feats[n].evidence_runs, coverage[n],
            k=k, coverage_power=coverage_power) * (s - raw_mean), 4)
        for n, s in scores.items()
    }
    # --- end of F1 challenger change (rest identical to production). ---
    mean_score = sum(scores.values()) / len(scores)
    strengths: dict[int, float] = {}
    for n, s in scores.items():
        factor, _ = adjustments.get(n, (1.0, ()))
        strengths[n] = exp(beta * (s - mean_score)) * factor
    floor = FLOOR_FRACTION * min(strengths.values())
    floored = set()
    for number in feats:
        if number not in strengths:
            strengths[number] = floor
            floored.add(number)
    probs = marginals(distribution(strengths))
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranked, probs)
    runners = []
    for number in sorted(feats):
        if number in probs:
            factor, reasons = adjustments.get(number, (1.0, ()))
            runners.append(RunnerForecast(
                number=number, name=names[number],
                ability_score=scores.get(number),
                strength=round(strengths[number], 6),
                pace_adjustment=factor, pace_reasons=reasons,
                p_win=round(probs[number][0], 4),
                p_top2=round(probs[number][1], 4),
                p_top3=round(probs[number][2], 4),
                mark=marks.get(number, ""),
                status=("unscored-floor-strength" if number in floored
                        else "forecast-uncalibrated"),
            ))
        else:
            runners.append(RunnerForecast(
                number=number, name=names[number],
                ability_score=scores.get(number),
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="insufficient-evidence",
            ))
    return RaceForecast(race.race_id, beta, PROBABILITY_STATUS,
                        tuple(runners), "ok")
