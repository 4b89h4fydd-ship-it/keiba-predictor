"""Staged pre-off score: observed recent form and matching condition evidence.

The active score does not use sectional rank or duplicate peak-finish scores.
Its conditional adjustment is capped at 25% and uses only observed earlier
runs on matching surface and within 150 m. Scores are not probabilities.
This model is experimental until authenticated pre-off performance validation.
"""
from __future__ import annotations

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
    """Collect observed recent form and condition evidence, not prior AI scores."""
    runs = observed_runs(horse, race, limit=5)
    qualities: list[float] = []
    comparable_qualities: list[float] = []
    distance = _number(race.get("distance") or race.get("distanceM"))
    surface = str(race.get("surface") or "").strip()
    for run in runs:
        finish = _number(run.get("finish"))
        field = _number(run.get("fieldSize"))
        if finish is None or field is None or field <= 1 or not (1 <= finish <= field):
            continue
        quality = (field - finish) / (field - 1)
        qualities.append(quality)
        prior_distance = _number(run.get("distance"))
        if (distance and prior_distance and abs(distance - prior_distance) <= 150
                and surface and str(run.get("surface") or "").strip() == surface):
            comparable_qualities.append(quality)

    weighted_form = None
    if qualities:
        weights = [5 - i for i in range(len(qualities))]
        weighted_form = sum(w * q for w, q in zip(weights, qualities)) / sum(weights)
    return {
        "recentForm": weighted_form,
        "conditionForm": sum(comparable_qualities) / len(comparable_qualities) if comparable_qualities else None,
        "conditionRuns": float(len(comparable_qualities)),
        "sample": float(len(qualities)),
    }


def rank_factor_model(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    """The only ranking for core score, marks, saved probabilities, and bets."""
    active = [h for h in horses if isinstance(h, dict) and not is_inactive_runner(h)]
    rows = []
    for horse in active:
        raw = collect_horse_raw_metrics(horse, race)
        past = analyze_past_performance(horse, race)
        recent = raw.get("recentForm")
        comparable = raw.get("conditionForm")
        condition_runs = int(raw.get("conditionRuns") or 0)
        strength = min(MAX_CONDITION_WEIGHT, CONDITION_WEIGHT_PER_RUN * condition_runs) if comparable is not None else 0.0
        score = (recent if comparable is None else
                 (1 - strength) * recent + strength * comparable) if recent is not None else 0.5
        factors = {
            "recentForm": raw.get("recentForm"),
            "conditionForm": raw.get("conditionForm"),
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
