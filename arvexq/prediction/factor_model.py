from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import analyze_past_performance, observed_runs
from arvexq.prediction.career_profile import profile_career

MODEL_VERSION = "arvexq-true-run-pure-sectional-45-35-20-v1"
PRIMARY_PILLARS = ("trueRun", "pure", "sectional")
SCORE_WEIGHTS = {"trueRun": .45, "pure": .35, "sectional": .20}

def _f(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _unit(value: Any) -> float | None:
    x = _f(value)
    if x is None:
        return None
    if x > 1.5:
        x /= 100.0
    return max(0.0, min(1.0, x))


def _first(*values: float | None) -> float | None:
    return next((v for v in values if v is not None), None)


def _runs(horse: dict[str, Any], race: dict[str, Any]) -> list[dict[str, Any]]:
    # Comparable historic observations, never future/same-day data.
    return observed_runs(horse, race, limit=None)


def _finish_quality(run: dict[str, Any]) -> float | None:
    finish = _f(run.get("finish", run.get("finishPosition", run.get("rank"))))
    field = _f(run.get("fieldSize")) or 12.0
    if finish is None or finish <= 0 or finish > field:
        return None
    field = max(2.0, field)
    return max(0.0, min(1.0, 1.0 - (finish - 1.0) / (field - 1.0)))


def _speed_index(run: dict[str, Any]) -> float | None:
    """Published/normalised speed index only. Never mix with raw m/s."""
    return _f(run.get("speedIndex"))


def _clock_speed(run: dict[str, Any]) -> float | None:
    """Derived average metres/second only.

    This is intentionally separate from speedIndex because their numerical scales
    are incompatible (e.g. index 80-100 vs roughly 15-19 m/s).
    """
    seconds = _f(run.get("timeSeconds"))
    distance = _f(run.get("distance"))
    if seconds and seconds > 0 and distance and distance > 0:
        return distance / seconds
    return None


def _mean(values: Iterable[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _component(horse: dict[str, Any], *names: str) -> float | None:
    evaluation = horse.get("integratedEvaluation") or {}
    components = evaluation.get("components") if isinstance(evaluation.get("components"), dict) else {}
    for name in names:
        if components.get(name) is not None:
            return _unit(components.get(name))
        if horse.get(name) is not None:
            return _unit(horse.get(name))
    return None


def _audit(horse: dict[str, Any]) -> dict[str, Any]:
    evaluation = horse.get("integratedEvaluation") or {}
    audit = evaluation.get("v218Audit") or evaluation.get("v217Audit") or {}
    return audit if isinstance(audit, dict) else {}


def _research(horse: dict[str, Any]) -> dict[str, Any]:
    evaluation = horse.get("integratedEvaluation") or {}
    factors = evaluation.get("researchFactors") or {}
    return factors if isinstance(factors, dict) else {}


def collect_horse_raw_metrics(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, float | None]:
    """Collect only pre-race evidence; do not invent factor percentages.

    Primary: ability / record / suitability / pace.
    Support: pedigree, weather/going response, same-day bias, draw, body weight,
    condition change, freshness/weight context when already measured, and connections.
    Missing data remains missing instead of being converted into a fake neutral score.
    """
    runs = _runs(horse, race)
    qualities = [_finish_quality(r) for r in runs]
    valid_q = [q for q in qualities if q is not None]
    recent_q = [q for q in qualities[:5] if q is not None]
    speed_indices = [_speed_index(r) for r in runs]
    valid_speed_indices = [v for v in speed_indices if v is not None]
    clock_speeds = [_clock_speed(r) for r in runs]
    valid_clock_speeds = [v for v in clock_speeds if v is not None]

    wins = top3 = completed = 0
    levels: list[float] = []
    prizes: list[float] = []
    for run in runs:
        finish = _f(run.get("finish", run.get("finishPosition", run.get("rank"))))
        if finish is not None and finish > 0:
            completed += 1
            wins += int(finish == 1)
            top3 += int(finish <= 3)
        level = _f(run.get("opponentLevel", run.get("levelScore")))
        if level is not None and level > 0:
            levels.append(level)
        prize = _f(run.get("racePrize1"))
        if prize is not None and prize > 0:
            prizes.append(prize)

    target_distance = _f(race.get("distance"))
    target_track = str(race.get("track") or "")
    target_condition = str(race.get("condition") or race.get("going") or "")
    target_surface = str(race.get("surface") or "")
    current_prize = _f(race.get("racePrize1"))

    same_distance: list[float] = []
    same_track: list[float] = []
    same_condition: list[float] = []
    same_surface: list[float] = []
    for run, quality in zip(runs, qualities):
        if quality is None:
            continue
        run_distance = _f(run.get("distance"))
        if target_distance and run_distance and abs(run_distance - target_distance) <= 100:
            same_distance.append(quality)
        if target_track and str(run.get("track") or "") == target_track:
            same_track.append(quality)
        run_condition = str(run.get("condition") or run.get("going") or "")
        if target_condition and run_condition == target_condition:
            same_condition.append(quality)
        if target_surface and str(run.get("surface") or "") == target_surface:
            same_surface.append(quality)

    past = analyze_past_performance(horse, race)
    career = profile_career(horse, race)
    audit = _audit(horse)
    research = _research(horse)
    evaluation = horse.get("integratedEvaluation") or {}
    class_edge = None
    if current_prize and current_prize > 0 and prizes:
        class_edge = (sum(prizes) / len(prizes)) / current_prize

    return {
        "ability_speed_index_peak": max(valid_speed_indices) if valid_speed_indices else None,
        "ability_speed_index_median": median(valid_speed_indices) if valid_speed_indices else None,
        "ability_clock_speed_peak": max(valid_clock_speeds) if valid_clock_speeds else None,
        "ability_clock_speed_median": median(valid_clock_speeds) if valid_clock_speeds else None,
        "ability_peak_finish": max(valid_q) if valid_q else None,
        "ability_sectional": _first(_unit(audit.get("sectional")), _component(horse, "lapScore")),
        "ability_true_run": _unit(audit.get("trueRun")),
        "ability_pure": _unit(audit.get("pure")),
        "ability_research": _unit(research.get("ability")),
        "record_career": _mean(valid_q),
        "record_recent": _mean(recent_q),
        "record_recent_context": past["recentFormQuality"] if past["datedRuns"]>=3 else None,
        "record_win_rate": wins / completed if completed else None,
        "record_top3_rate": top3 / completed if completed else None,
        "record_career_stability": career["stability"],
        "record_level": _mean(levels),
        "record_class_edge": class_edge,
        "record_representative": _component(horse, "representative"),
        "record_race_performance": _component(horse, "racePerformance"),
        "record_class_research": _unit(research.get("classLevel")),
        "record_form_research": _unit(research.get("form")),
        "suit_distance_history": _mean(same_distance),
        "suit_comparable_recent": past["comparableQuality"] if past["comparableRuns"]>=2 else None,
        "suit_comparable_career": career["comparableQuality"] if career["comparableRuns"]>=2 else None,
        "suit_track_history": _mean(same_track),
        "suit_going_history": _mean(same_condition),
        "suit_surface_history": _mean(same_surface),
        "suit_distance_model": _component(horse, "distanceFit"),
        "suit_track_model": _component(horse, "courseFit", "trackFit"),
        "suit_going_model": _component(horse, "goingFit", "conditionFit"),
        "suit_surface_model": _component(horse, "surfaceSuitabilityScore"),
        "suit_research": _unit(research.get("suitability")),
        "pace_scenario": _unit(audit.get("positionScenario")),
        "pace_state": _unit(audit.get("stateConsistency")),
        "pace_front_hold_recent": (1 - past["frontFadeCount"]/past["datedRuns"])
            if past["datedRuns"]>=3 else None,
        "pace_research": _unit(research.get("pace")),
        "pace_track_speed_fit": _unit(audit.get("trackSpeedFit")),
        "pace_hidden_effort": _unit(audit.get("hiddenEffort")),
        "support_pedigree": _component(horse, "pedigreeScore"),
        "support_pedigree_distance": _component(horse, "distanceSuitabilityScore"),
        "support_pedigree_surface": _component(horse, "surfaceSuitabilityScore"),
        "support_weather": _component(horse, "weatherFit", "weatherScore"),
        "support_draw": _component(horse, "drawScore"),
        "support_body": _component(horse, "bodyWeightScore"),
        "support_body_change": _component(horse, "bodyWeightChangeScore", "weightChangeScore"),
        "support_carried_weight": _component(horse, "carriedWeightScore", "weightReliefScore"),
        "support_condition_change": _component(horse, "conditionChangeScore"),
        "support_freshness": _component(horse, "freshnessScore", "restSuitabilityScore"),
        "support_age_sex": _component(horse, "ageSexScore"),
        "support_jockey": _component(horse, "jockeyScore", "jockeyResults"),
        "support_trainer": _component(horse, "trainerScore", "trainerResults"),
        "support_bias": _f(evaluation.get("sameDayMarkAdjustment")),
        "support_bias_model": _component(horse, "biasScore", "trackBiasScore"),
        "support_connections": _unit(research.get("connections")),
        "support_pedigree_research": _unit(research.get("pedigree")),
        "sample": float(len(runs)),
    }



def _sectional_from_history(horse: dict[str, Any], race: dict[str, Any]) -> float | None:
    observations = []
    for run in observed_runs(horse, race, limit=5):
        rank = _f(run.get("last3fRank") or run.get("last600Rank"))
        field = _f(run.get("fieldSize"))
        if rank is not None and field is not None and field > 1 and 1 <= rank <= field:
            observations.append((field-rank)/(field-1))
    return _mean(observations)


def rank_factor_model(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    """Authoritative TRUE RUN 45 + PURE 35 + SECTIONAL 20. Not hit probability."""
    active = [h for h in horses if isinstance(h, dict) and not is_inactive_runner(h)]
    rows = []
    for horse in active:
        raw = collect_horse_raw_metrics(horse, race)
        past = analyze_past_performance(horse, race)
        ev = horse.get("integratedEvaluation") or {}
        audit = ev.get("v218Audit") or ev.get("v217Audit") or {}
        if not isinstance(audit, dict):
            audit = {}
        factors = {
            "trueRun": _first(_unit(audit.get("trueRun")),
                              _unit(raw.get("ability_true_run")),
                              _unit(past.get("recentFormQuality"))),
            "pure": _first(_unit(audit.get("pure")), _unit(raw.get("ability_pure"))),
            "sectional": _first(_unit(audit.get("sectional")),
                                _unit(raw.get("ability_sectional")),
                                _sectional_from_history(horse, race)),
        }
        available = sum(value is not None for value in factors.values())
        score = sum(weight * (factors[key] if factors[key] is not None else .5)
                    for key, weight in SCORE_WEIGHTS.items())
        rows.append({
            "horse": horse, "raw": raw, "pastPerformance": past,
            "careerProfile": profile_career(horse, race),
            "score": score, "factors": factors,
            "pillarScores": factors.copy(), "sample": int(raw.get("sample") or 0),
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
