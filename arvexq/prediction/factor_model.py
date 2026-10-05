from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from arvexq.core.runner_status import is_inactive_runner

MODEL_VERSION = "arvexq-four-pillar-consensus-v4"
PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")

# Correlated measurements from the same underlying observation are collapsed first.
# This prevents one past run from becoming several independent votes merely because
# it produced peak/median, career/recent and win/top3 statistics at the same time.
SIGNAL_FAMILIES = {
    "ability": (
        ("ability_speed_peak", "ability_speed_median"),
        ("ability_peak_finish",),
        ("ability_sectional",),
        ("ability_true_run",),
        ("ability_pure",),
        ("ability_research",),
    ),
    "record": (
        ("record_career", "record_recent"),
        ("record_win_rate", "record_top3_rate"),
        ("record_level", "record_class_edge", "record_class_research"),
        ("record_representative",),
        ("record_race_performance",),
        ("record_form_research",),
    ),
    "suitability": (
        ("suit_distance_history", "suit_track_history", "suit_going_history", "suit_surface_history"),
        ("suit_distance_model", "suit_track_model", "suit_going_model", "suit_surface_model"),
        ("suit_research",),
    ),
    "pace": (
        ("pace_scenario",),
        ("pace_state",),
        ("pace_research",),
        ("pace_track_speed_fit",),
        ("pace_hidden_effort",),
    ),
    "support": (
        ("support_pedigree", "support_pedigree_distance", "support_pedigree_surface", "support_pedigree_research"),
        ("support_body", "support_body_change", "support_carried_weight"),
        ("support_weather",),
        ("support_draw",),
        ("support_condition_change", "support_freshness"),
        ("support_age_sex",),
        ("support_jockey", "support_trainer", "support_connections"),
        ("support_bias", "support_bias_model"),
    ),
}


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


def _runs(horse: dict[str, Any]) -> list[dict[str, Any]]:
    rows = horse.get("allPastRuns") or horse.get("recentRaces") or []
    return [r for r in rows if isinstance(r, dict)]


def _finish_quality(run: dict[str, Any]) -> float | None:
    finish = _f(run.get("finish", run.get("finishPosition", run.get("rank"))))
    field = _f(run.get("fieldSize")) or 12.0
    if finish is None or finish <= 0 or finish > field:
        return None
    field = max(2.0, field)
    return max(0.0, min(1.0, 1.0 - (finish - 1.0) / (field - 1.0)))


def _speed_raw(run: dict[str, Any]) -> float | None:
    direct = _f(run.get("speedIndex"))
    if direct is not None:
        return direct
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
    runs = _runs(horse)
    qualities = [_finish_quality(r) for r in runs]
    valid_q = [q for q in qualities if q is not None]
    recent_q = [q for q in qualities[:5] if q is not None]
    speeds = [_speed_raw(r) for r in runs]
    valid_speeds = [s for s in speeds if s is not None]

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

    audit = _audit(horse)
    research = _research(horse)
    evaluation = horse.get("integratedEvaluation") or {}
    class_edge = None
    if current_prize and current_prize > 0 and prizes:
        class_edge = (sum(prizes) / len(prizes)) / current_prize

    return {
        "ability_speed_peak": max(valid_speeds) if valid_speeds else None,
        "ability_speed_median": median(valid_speeds) if valid_speeds else None,
        "ability_peak_finish": max(valid_q) if valid_q else None,
        "ability_sectional": _first(_unit(audit.get("sectional")), _component(horse, "lapScore")),
        "ability_true_run": _unit(audit.get("trueRun")),
        "ability_pure": _unit(audit.get("pure")),
        "ability_research": _unit(research.get("ability")),
        "record_career": _mean(valid_q),
        "record_recent": _mean(recent_q),
        "record_win_rate": wins / completed if completed else None,
        "record_top3_rate": top3 / completed if completed else None,
        "record_level": _mean(levels),
        "record_class_edge": class_edge,
        "record_representative": _component(horse, "representative"),
        "record_race_performance": _component(horse, "racePerformance"),
        "record_class_research": _unit(research.get("classLevel")),
        "record_form_research": _unit(research.get("form")),
        "suit_distance_history": _mean(same_distance),
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


def _relative(values: list[float | None]) -> list[float | None]:
    """Race-relative rank percentile. No magnitude coefficient is introduced."""
    valid = sorted(v for v in values if v is not None)
    if not valid:
        return [None for _ in values]
    if len(valid) == 1:
        return [0.5 if v is not None else None for v in values]
    out: list[float | None] = []
    for value in values:
        if value is None:
            out.append(None)
            continue
        less = sum(1 for x in valid if x < value)
        equal = sum(1 for x in valid if x == value)
        rank = less + (equal - 1) / 2.0
        out.append(rank / (len(valid) - 1))
    return out


def _pillar(values: list[float | None]) -> float | None:
    available = [v for v in values if v is not None]
    return float(median(available)) if available else None


def _rank_map(rows: list[dict[str, Any]], key: str) -> dict[int, int]:
    """Rank equal evidence equally; missing evidence must never become horse-number rank."""
    values = sorted({float(row[key]) for row in rows if row.get(key) is not None}, reverse=True)
    by_value = {value: idx + 1 for idx, value in enumerate(values)}
    missing_rank = len(values) + 1
    return {
        id(row): by_value.get(float(row[key]), missing_rank) if row.get(key) is not None else missing_rank
        for row in rows
    }


def rank_factor_model(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    active = [h for h in horses if isinstance(h, dict) and not is_inactive_runner(h)]
    rows = [{"horse": h, "raw": collect_horse_raw_metrics(h, race)} for h in active]
    if not rows:
        return []

    metric_names = sorted({k for row in rows for k in row["raw"] if k != "sample"})
    relative_by_metric = {
        metric: _relative([row["raw"].get(metric) for row in rows])
        for metric in metric_names
    }
    groups = {
        "ability": [m for m in metric_names if m.startswith("ability_")],
        "record": [m for m in metric_names if m.startswith("record_")],
        "suitability": [m for m in metric_names if m.startswith("suit_")],
        "pace": [m for m in metric_names if m.startswith("pace_")],
        "support": [m for m in metric_names if m.startswith("support_")],
    }

    for i, row in enumerate(rows):
        row["metricRelative"] = {m: relative_by_metric[m][i] for m in metric_names}
        scores: dict[str, float | None] = {}
        counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}
        for pillar, metrics in groups.items():
            vals = [relative_by_metric[m][i] for m in metrics]
            counts[pillar] = sum(v is not None for v in vals)

            # Collapse correlated metrics inside each evidence family before the
            # pillar median. Each family therefore contributes at most one signal.
            collapsed: list[float] = []
            for family in SIGNAL_FAMILIES[pillar]:
                family_value = _pillar([relative_by_metric[m][i] for m in family])
                if family_value is not None:
                    collapsed.append(family_value)
            scores[pillar] = _pillar(collapsed)
            family_counts[pillar] = len(collapsed)
        row["pillarScores"] = scores
        row["evidenceCounts"] = counts
        row["evidenceFamilyCounts"] = family_counts
        row["sample"] = int(row["raw"].get("sample") or 0)
        row["primaryEvidenceCount"] = sum(counts[p] for p in PRIMARY_PILLARS)
        row["primaryPillarCoverage"] = sum(counts[p] > 0 for p in PRIMARY_PILLARS)
        for pillar in (*PRIMARY_PILLARS, "support"):
            row[pillar] = scores[pillar]

    # If the new model has no primary evidence at all, do not manufacture a ranking.
    # The caller can keep the existing prediction or flag the race as data-insufficient.
    if not any(row["primaryEvidenceCount"] > 0 for row in rows):
        return []

    pillar_ranks = {pillar: _rank_map(rows, pillar) for pillar in (*PRIMARY_PILLARS, "support")}
    for row in rows:
        row["pillarRanks"] = {pillar: pillar_ranks[pillar][id(row)] for pillar in pillar_ranks}
        row["primaryRankSum"] = sum(row["pillarRanks"][p] for p in PRIMARY_PILLARS)
        row["pairwiseWins"] = 0
        row["pairwiseLosses"] = 0
        row["pairwiseTies"] = 0
        row["supportTieBreakWins"] = 0

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            aw = bw = compared = 0
            for pillar in PRIMARY_PILLARS:
                av, bv = a[pillar], b[pillar]
                if av is None or bv is None:
                    continue
                compared += 1
                if av == bv:
                    continue
                if av > bv:
                    aw += 1
                else:
                    bw += 1
            if aw > bw:
                a["pairwiseWins"] += 1
                b["pairwiseLosses"] += 1
            elif bw > aw:
                b["pairwiseWins"] += 1
                a["pairwiseLosses"] += 1
            else:
                sa, sb = a["support"], b["support"]
                # Support is a tie-break only when primary evidence was actually compared.
                if compared > 0 and sa is not None and sb is not None and sa != sb:
                    winner, loser = (a, b) if sa > sb else (b, a)
                    winner["pairwiseWins"] += 1
                    loser["pairwiseLosses"] += 1
                    winner["supportTieBreakWins"] += 1
                else:
                    a["pairwiseTies"] += 1
                    b["pairwiseTies"] += 1

    rows.sort(
        key=lambda r: (
            -r["pairwiseWins"],
            r["pairwiseLosses"],
            -r["primaryPillarCoverage"],
            r["primaryRankSum"],
            r["pillarRanks"]["support"],
            -r["sample"],
            int(r["horse"].get("horseNumber") or 999),
        )
    )
    field = max(1, len(rows) - 1)
    for idx, row in enumerate(rows, 1):
        row["rank"] = idx
        row["dominanceScore"] = round(100.0 * row["pairwiseWins"] / field, 1) if len(rows) > 1 else 50.0
        row["modelVersion"] = MODEL_VERSION
    return rows
