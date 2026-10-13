"""Staged pre-off score: observed recent form and matching condition evidence.

The active score does not use sectional rank or duplicate peak-finish scores.
Its conditional adjustment is capped at 25% and uses only observed earlier
runs on matching surface and within 150 m. Scores are not probabilities.
This model is experimental until authenticated pre-off performance validation.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import analyze_past_performance, observed_runs
from arvexq.prediction.career_profile import profile_career

MODEL_VERSION = "arvexq-form-condition-no-sectional-proposal-v1"
PRIMARY_PILLARS = ("recentForm", "conditionForm")
CONDITION_WEIGHT_PER_RUN = 0.08
MAX_CONDITION_WEIGHT = 0.25


def _number(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def collect_horse_raw_metrics(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, float | None]:
    """Collect the three measured axes from five earlier races, not prior AI scores."""
    runs = observed_runs(horse, race, limit=5)
    qualities: list[float] = []
    closing: list[float] = []
    for run in runs:
        finish = _number(run.get("finish"))
        field = _number(run.get("fieldSize"))
        if finish is None or field is None or field <= 1 or not (1 <= finish <= field):
            continue
        qualities.append((field - finish) / (field - 1))
        closing_rank = _number(run.get("last3fRank") or run.get("last600Rank"))
        if closing_rank is not None and 1 <= closing_rank <= field:
            closing.append((field - closing_rank) / (field - 1))
        else:
            percentile = _number(run.get("last3fPercentile"))
            if percentile is not None and 0 <= percentile <= 1:
                closing.append(percentile)

    weighted_form = None
    peak_ability = None
    if qualities:
        weights = [5 - i for i in range(len(qualities))]
        weighted_form = sum(w * q for w, q in zip(weights, qualities)) / sum(weights)
        peak_ability = (max(qualities) + median(qualities)) / 2
    sectional = sum(closing) / len(closing) if closing else None
    return {
        "trueRun": weighted_form,
        "pure": peak_ability,
        "sectional": sectional,
        "sample": float(len(qualities)),
    }


def rank_factor_model(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    """The only ranking for core score, marks, saved probabilities, and bets."""
    active = [h for h in horses if isinstance(h, dict) and not is_inactive_runner(h)]
    rows = []
    for horse in active:
        raw = collect_horse_raw_metrics(horse, race)
        past = analyze_past_performance(horse, race)
        recent = raw.get("trueRun")
        comparable = past.get("comparableQuality")
        condition_runs = int(past.get("comparableRuns") or 0)
        strength = min(MAX_CONDITION_WEIGHT, CONDITION_WEIGHT_PER_RUN * condition_runs) if comparable is not None else 0.0
        score = ((1 - strength) * recent + strength * comparable
                 if recent is not None else 0.5)
        factors = {
            "recentForm": raw.get("trueRun"),
            "conditionForm": past.get("comparableQuality"),
        }
        available = sum(value is not None for value in factors.values())
        rows.append({
            "horse": horse, "raw": raw,
            "pastPerformance": past,
            "careerProfile": profile_career(horse, race),
            "score": score if score is not None else 0.5,
            "factors": factors, "pillarScores": factors.copy(),
            "sample": int(raw.get("sample") or 0),
            "evidenceCounts": {k: int(v is not None) for k, v in factors.items()},
            "evidenceFamilyCounts": {k: int(v is not None) for k, v in factors.items()},
            "primaryPillarCoverage": available, "primaryEvidenceCount": available,
            "supportTieBreakWins": 0, "modelVersion": MODEL_VERSION,
        })
    if not any(row["primaryPillarCoverage"] for row in rows):
        return []
    for key in PRIMARY_PILLARS:
        distinct = sorted({r["factors"][key] for r in rows if r["factors"][key] is not None},
                          reverse=True)
        for row in rows:
            val = row["factors"][key]
            row.setdefault("pillarRanks", {})[key] = (
                distinct.index(val) + 1 if val is not None else len(distinct) + 1
            )
    rows.sort(key=lambda row: (-row["score"], -row["primaryPillarCoverage"],
                               -row["sample"], int(row["horse"].get("horseNumber") or 999)))
    for i, row in enumerate(rows):
        row["rank"] = i + 1
        row["dominanceScore"] = round(row["score"] * 100, 2)
        row["pairwiseWins"] = sum(row["score"] > other["score"] for other in rows if other is not row)
        row["pairwiseLosses"] = sum(row["score"] < other["score"] for other in rows if other is not row)
        row["pairwiseTies"] = len(rows) - 1 - row["pairwiseWins"] - row["pairwiseLosses"]
        row["metricRelative"] = {}
    return rows
