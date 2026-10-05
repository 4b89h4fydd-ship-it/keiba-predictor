from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from arvexq.core.runner_status import is_inactive_runner

MODEL_VERSION = "arvexq-four-pillar-consensus-v1"
PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")


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


def _max(values: Iterable[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return max(vals) if vals else None


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
    """Collect pre-race evidence without assigning arbitrary factor percentages.

    The four primary pillars are ability, record, suitability and pace. Pedigree,
    weather response, bias/draw, body weight, condition changes and connections are
    collected as support signals. Missing evidence stays missing; it is never replaced
    with an invented neutral performance.
    """
    runs = _runs(horse)
    qualities = [_finish_quality(r) for r in runs]
    valid_q = [q for q in qualities if q is not None]
    recent_q = [q for q in qualities[:5] if q is not None]
    speeds = [_speed_raw(r) for r in runs]
    valid_speeds = [s for s in speeds if s is not None]

    wins = top3 = completed = 0
    levels: list[float] = []
    for run in runs:
        finish = _f(run.get("finish", run.get("finishPosition", run.get("rank"))))
        if finish is not None and finish > 0:
            completed += 1
            wins += int(finish == 1)
            top3 += int(finish <= 3)
        level = _f(run.get("opponentLevel", run.get("levelScore", run.get("racePrize1"))))
        if level is not None and level > 0:
            levels.append(level)

    target_distance = _f(race.get("distance"))
    target_track = str(race.get("track") or "")
    target_condition = str(race.get("condition") or race.get("going") or "")

    same_distance: list[float] = []
    same_track: list[float] = []
    same_condition: list[float] = []
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

    audit = _audit(horse)
    research = _research(horse)
    evaluation = horse.get("integratedEvaluation") or {}

    return {
        # 能力: raw speed / peak output / sectional / TRUE RUN.
        "ability_speed_peak": max(valid_speeds) if valid_speeds else None,
        "ability_speed_median": median(valid_speeds) if valid_speeds else None,
        "ability_peak_finish": max(valid_q) if valid_q else None,
        "ability_sectional": _unit(audit.get("sectional")) or _component(horse, "lapScore"),
        "ability_true_run": _unit(audit.get("trueRun")),
        "ability_pure": _unit(audit.get("pure")),

        # 実績: career/recent results, wins/top3, class/opponent level, representative run.
        "record_career": _mean(valid_q),
        "record_recent": _mean(recent_q),
        "record_win_rate": wins / completed if completed else None,
        "record_top3_rate": top3 / completed if completed else None,
        "record_level": _mean(levels),
        "record_representative": _component(horse, "representative"),
        "record_race_performance": _component(horse, "racePerformance"),

        # 適性: distance/course/going evidence from actual past performance + stored fits.
        "suit_distance_history": _mean(same_distance),
        "suit_track_history": _mean(same_track),
        "suit_going_history": _mean(same_condition),
        "suit_distance_model": _component(horse, "distanceFit"),
        "suit_track_model": _component(horse, "courseFit", "trackFit"),
        "suit_going_model": _component(horse, "goingFit", "conditionFit"),

        # 展開: scenario/pace diagnostics. No odds or post-race result is used.
        "pace_scenario": _unit(audit.get("positionScenario")),
        "pace_state": _unit(audit.get("stateConsistency")),
        "pace_research": _unit(research.get("pace")),
        "pace_track_speed_fit": _unit(audit.get("trackSpeedFit")),

        # 補助: pedigree/weather/bias/draw/body/condition change/connections.
        "support_pedigree": _component(horse, "pedigreeScore"),
        "support_pedigree_distance": _component(horse, "distanceSuitabilityScore"),
        "support_pedigree_surface": _component(horse, "surfaceSuitabilityScore"),
        "support_weather": _component(horse, "weatherFit", "weatherScore"),
        "support_draw": _component(horse, "drawScore"),
        "support_body": _component(horse, "bodyWeightScore"),
        "support_condition_change": _component(horse, "conditionChangeScore"),
        "support_jockey": _component(horse, "jockeyScore", "jockeyResults"),
        "support_trainer": _component(horse, "trainerScore", "trainerResults"),
        "support_bias": _f(evaluation.get("sameDayMarkAdjustment")),
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
    ordered = sorted(
        rows,
        key=lambda r: (
            r[key] is None,
            -float(r[key] or 0.0),
            int(r["horse"].get("horseNumber") or 999),
        ),
    )
    return {id(row): i + 1 for i, row in enumerate(ordered)}


def rank_factor_model(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    active = [h for h in horses if isinstance(h, dict) and not is_inactive_runner(h)]
    rows = [{"horse": h, "raw": collect_horse_raw_metrics(h, race)} for h in active]
    if not rows:
        return []

    metric_names = sorted({k for row in rows for k in row["raw"] if k != "sample"})
    relative_by_metric: dict[str, list[float | None]] = {}
    for metric in metric_names:
        relative_by_metric[metric] = _relative([row["raw"].get(metric) for row in rows])

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
        for pillar, metrics in groups.items():
            vals = [relative_by_metric[m][i] for m in metrics]
            scores[pillar] = _pillar(vals)
            counts[pillar] = sum(v is not None for v in vals)
        row["pillarScores"] = scores
        row["evidenceCounts"] = counts
        row["sample"] = int(row["raw"].get("sample") or 0)
        for pillar in (*PRIMARY_PILLARS, "support"):
            row[pillar] = scores[pillar]

    pillar_ranks = {pillar: _rank_map(rows, pillar) for pillar in (*PRIMARY_PILLARS, "support")}
    for row in rows:
        row["pillarRanks"] = {pillar: pillar_ranks[pillar][id(row)] for pillar in pillar_ranks}
        row["primaryRankSum"] = sum(row["pillarRanks"][p] for p in PRIMARY_PILLARS)
        row["pairwiseWins"] = 0
        row["pairwiseLosses"] = 0
        row["pairwiseTies"] = 0
        row["supportTieBreakWins"] = 0

    # Primary pillars decide every head-to-head comparison. Support factors are allowed
    # to decide only a 2-2/insufficient-evidence tie, so they can influence close calls
    # without overruling clear ability/record/suitability/pace superiority.
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            aw = bw = 0
            for pillar in PRIMARY_PILLARS:
                av, bv = a[pillar], b[pillar]
                if av is None or bv is None or av == bv:
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
                if sa is not None and sb is not None and sa != sb:
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
