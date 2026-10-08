from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Any, Callable, Iterable

from arvexq.prediction.jra_class_evidence import class_ordinal

FEATURE_SCHEMA_VERSION = "arvexq-mass-features-v2-temporal-and-speed-separation"

# This module is intentionally isolated from factor_model.py/final_marks.py.
# It generates only pre-race features. It does not read the current race result,
# payouts, finish order, or any post-race target field.
FORBIDDEN_CURRENT_RACE_KEYS = {
    "result",
    "results",
    "finishers",
    "payout",
    "payouts",
    "winner",
    "winnerHorseNumber",
    "actualFlow",
    "finalOrder",
    "confirmedResult",
}

WINDOWS: tuple[int | None, ...] = (1, 3, 5, 10, None)
DISTANCE_BANDS = (100, 200, 400)


def _f(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _s(value: Any) -> str:
    return str(value or "").strip()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _mean(values: Iterable[float]) -> float | None:
    vals = list(values)
    return sum(vals) / len(vals) if vals else None


def _std(values: Iterable[float]) -> float | None:
    vals = list(values)
    if not vals:
        return None
    m = sum(vals) / len(vals)
    return sqrt(sum((x - m) ** 2 for x in vals) / len(vals))


def _quantile(values: Iterable[float], q: float) -> float | None:
    vals = sorted(values)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    p = _clamp(q, 0.0, 1.0) * (len(vals) - 1)
    lo = int(p)
    hi = min(len(vals) - 1, lo + 1)
    frac = p - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def _trend(values: Iterable[float]) -> float | None:
    vals = list(values)
    n = len(vals)
    if n < 2:
        return None
    # Input order is newest -> oldest. Positive means improving toward the latest run.
    xs = list(range(n))
    xm = sum(xs) / n
    ym = sum(vals) / n
    den = sum((x - xm) ** 2 for x in xs)
    if den <= 0:
        return None
    slope_oldward = sum((x - xm) * (y - ym) for x, y in zip(xs, vals)) / den
    return -slope_oldward


def _finish(run: dict[str, Any]) -> float | None:
    return _f(run.get("finish", run.get("finishPosition", run.get("rank"))))


def _field_size(run: dict[str, Any]) -> float | None:
    return _f(run.get("fieldSize", run.get("field", run.get("runners"))))


def _finish_quality(run: dict[str, Any]) -> float | None:
    fin = _finish(run)
    field = _field_size(run)
    if fin is None or fin <= 0:
        return None
    if field is None or field < 2:
        field = max(2.0, fin)
    if fin > field:
        return None
    return _clamp(1.0 - (fin - 1.0) / (field - 1.0), 0.0, 1.0)


def _speed(run: dict[str, Any]) -> float | None:
    """Published index only; never merge with metres/second."""
    return _f(run.get("speedIndex"))


def _clock_speed(run: dict[str, Any]) -> float | None:
    seconds = _f(run.get("timeSeconds"))
    distance = _f(run.get("distance"))
    if seconds and seconds > 0 and distance and distance > 0:
        return distance / seconds
    return None


def _late_speed(run: dict[str, Any]) -> float | None:
    # Prefer race-relative JRA closing evidence. Raw last3F seconds are never fed
    # directly because course/distance/going make cross-race seconds incomparable.
    direct = _f(run.get("last3FPercentile"))
    if direct is not None:
        return max(0.0, min(1.0, direct))
    rank = _f(run.get("last3FRank"))
    field = _f(run.get("fieldSize"))
    if rank is not None and field is not None and field >= 2 and 1 <= rank <= field:
        return max(0.0, min(1.0, 1.0 - (rank - 1.0) / (field - 1.0)))
    return _f(
        run.get(
            "last3FIndex",
            run.get("sectionalIndex", run.get("closingIndex", run.get("lateSpeedIndex"))),
        )
    )


def _early_speed(run: dict[str, Any]) -> float | None:
    return _f(run.get("earlySpeedIndex", run.get("first3FIndex", run.get("paceIndex"))))


def _position(run: dict[str, Any]) -> float | None:
    for key in ("corner4", "fourthCorner", "position4", "lastCornerPosition", "position"):
        value = _f(run.get(key))
        if value is not None and value > 0:
            return value
    return None


def _position_quality(run: dict[str, Any]) -> float | None:
    pos = _position(run)
    field = _field_size(run)
    if pos is None or pos <= 0:
        return None
    if field is None or field < 2:
        field = max(2.0, pos)
    return _clamp(1.0 - (pos - 1.0) / (field - 1.0), 0.0, 1.0)


def _opponent_level(run: dict[str, Any]) -> float | None:
    direct = _f(run.get("opponentLevel", run.get("levelScore", run.get("raceLevel"))))
    if direct is not None and direct > 0:
        return direct
    # Class parsed from the historical race title is a candidate ML feature only.
    # It is not promoted into the production four-pillar marks after the challenger
    # showed no win-rate gain.
    parsed = class_ordinal(run.get("title") or run.get("raceName"))
    return float(parsed) if parsed is not None else None


def _prize(run: dict[str, Any]) -> float | None:
    return _f(run.get("racePrize1", run.get("firstPrize", run.get("prize"))))


def _margin(run: dict[str, Any]) -> float | None:
    return _f(run.get("margin", run.get("finishMargin", run.get("behindWinner"))))


def _carried_weight(run: dict[str, Any]) -> float | None:
    return _f(run.get("carriedWeight", run.get("weight", run.get("assignedWeight"))))


def _body_weight(run: dict[str, Any]) -> float | None:
    return _f(run.get("bodyWeight"))


def _distance(run: dict[str, Any]) -> float | None:
    return _f(run.get("distance"))


def _win_flag(run: dict[str, Any]) -> float | None:
    fin = _finish(run)
    return None if fin is None or fin <= 0 else float(fin == 1)


def _top2_flag(run: dict[str, Any]) -> float | None:
    fin = _finish(run)
    return None if fin is None or fin <= 0 else float(fin <= 2)


def _top3_flag(run: dict[str, Any]) -> float | None:
    fin = _finish(run)
    return None if fin is None or fin <= 0 else float(fin <= 3)


RUN_METRICS: dict[str, Callable[[dict[str, Any]], float | None]] = {
    "finish_quality": _finish_quality,
    "win_flag": _win_flag,
    "top2_flag": _top2_flag,
    "top3_flag": _top3_flag,
    "speed": _speed,
    "clock_speed": _clock_speed,
    "early_speed": _early_speed,
    "late_speed": _late_speed,
    "position_quality": _position_quality,
    "opponent_level": _opponent_level,
    "prize": _prize,
    "margin": _margin,
    "carried_weight": _carried_weight,
    "body_weight": _body_weight,
    "distance": _distance,
}


@dataclass(frozen=True)
class RaceContext:
    track: str
    surface: str
    condition: str
    distance: float | None
    circuit: str
    race_class: str


def _race_context(race: dict[str, Any]) -> RaceContext:
    for key in FORBIDDEN_CURRENT_RACE_KEYS:
        if key in race:
            # Presence is allowed in a post-race object, but this feature factory never reads it.
            # Explicitly keeping the guard list here makes leakage audits mechanical.
            pass
    return RaceContext(
        track=_s(race.get("track")),
        surface=_s(race.get("surface")),
        condition=_s(race.get("condition", race.get("going"))),
        distance=_f(race.get("distance")),
        circuit=_s(race.get("circuit")),
        race_class=_s(race.get("raceClass", race.get("className"))),
    )


def _runs(horse: dict[str, Any], race_date: str = "") -> list[dict[str, Any]]:
    rows = horse.get("allPastRuns") or horse.get("recentRaces") or []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        history_date = str(row.get("date") or row.get("raceDate") or "")[:10]
        # No future/same-day leakage into the previous-start training features.
        # Historical missing dates are permitted for backwards compatibility,
        # but labelled snapshots are generated only from genuine pre-off captures.
        if race_date and history_date and history_date >= race_date:
            continue
        out.append(row)
    return out


def _filter_sets(runs: list[dict[str, Any]], ctx: RaceContext) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"all": runs}
    out["same_track"] = [r for r in runs if ctx.track and _s(r.get("track")) == ctx.track]
    out["same_surface"] = [r for r in runs if ctx.surface and _s(r.get("surface")) == ctx.surface]
    out["same_condition"] = [
        r for r in runs if ctx.condition and _s(r.get("condition", r.get("going"))) == ctx.condition
    ]
    out["same_track_surface"] = [
        r
        for r in runs
        if ctx.track
        and ctx.surface
        and _s(r.get("track")) == ctx.track
        and _s(r.get("surface")) == ctx.surface
    ]
    # Raw metres/second observations are non-comparable across racing conditions.
    # Only matched track, surface, going and near-distance evidence is retained.
    if (ctx.track and ctx.surface and ctx.condition and ctx.distance is not None):
        out["matched_clock_context"] = [
            r for r in out["same_track_surface"]
            if _s(r.get("condition",r.get("going")))==ctx.condition
            and _distance(r) is not None
            and abs(float(_distance(r))-ctx.distance)<=100
        ]
    out["same_surface_condition"] = [
        r
        for r in runs
        if ctx.surface
        and ctx.condition
        and _s(r.get("surface")) == ctx.surface
        and _s(r.get("condition", r.get("going"))) == ctx.condition
    ]
    for band in DISTANCE_BANDS:
        name = f"distance_{band}"
        out[name] = [
            r
            for r in runs
            if ctx.distance is not None
            and _distance(r) is not None
            and abs(float(_distance(r)) - ctx.distance) <= band
        ]
        out[f"same_track_{name}"] = [
            r
            for r in out[name]
            if ctx.track and _s(r.get("track")) == ctx.track
        ]
        out[f"same_surface_{name}"] = [
            r
            for r in out[name]
            if ctx.surface and _s(r.get("surface")) == ctx.surface
        ]
    return out


def _aggregate_metric(rows: list[dict[str, Any]], fn: Callable[[dict[str, Any]], float | None]) -> dict[str, float]:
    vals = [v for v in (fn(r) for r in rows) if v is not None]
    if not vals:
        return {}
    out: dict[str, float] = {
        "count": float(len(vals)),
        "mean": float(sum(vals) / len(vals)),
        "median": float(median(vals)),
        "max": float(max(vals)),
        "min": float(min(vals)),
        "last": float(vals[0]),
    }
    sd = _std(vals)
    if sd is not None:
        out["std"] = float(sd)
    q25 = _quantile(vals, 0.25)
    q75 = _quantile(vals, 0.75)
    if q25 is not None:
        out["q25"] = float(q25)
    if q75 is not None:
        out["q75"] = float(q75)
    trend = _trend(vals)
    if trend is not None:
        out["trend"] = float(trend)
    if len(vals) >= 2:
        out["latest_minus_mean"] = float(vals[0] - sum(vals) / len(vals))
        out["latest_minus_median"] = float(vals[0] - median(vals))
        out["range"] = float(max(vals) - min(vals))
    return out


def _static_features(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    direct = {
        "horse_number": horse.get("horseNumber"),
        "frame_number": horse.get("frameNumber"),
        "age": horse.get("age"),
        "carried_weight": horse.get("carriedWeight", horse.get("weight")),
        "body_weight": horse.get("bodyWeight"),
        "body_weight_change": horse.get("bodyWeightChange", horse.get("weightChange")),
        "days_since_last": horse.get("daysSinceLast", horse.get("restDays")),
        "distance": race.get("distance"),
        "race_prize1": race.get("racePrize1"),
    }
    for key, value in direct.items():
        x = _f(value)
        if x is not None:
            out[f"static::{key}"] = x

    # Market features are isolated by namespace so ability/win training can exclude them.
    odds = _f(horse.get("winOdds"))
    pop = _f(horse.get("popularity"))
    if odds is not None and odds > 0:
        out["market::win_odds"] = odds
        out["market::implied_raw"] = 1.0 / odds
    if pop is not None and pop > 0:
        out["market::popularity"] = pop

    sex = _s(horse.get("sex"))
    if sex:
        out[f"category::sex::{sex}"] = 1.0
    for namespace, value in (
        ("track", race.get("track")),
        ("surface", race.get("surface")),
        ("condition", race.get("condition", race.get("going"))),
        ("circuit", race.get("circuit")),
        ("race_class", race.get("raceClass", race.get("className"))),
        ("jockey", horse.get("jockey")),
        ("trainer", horse.get("trainer")),
        ("sire", (horse.get("pedigree") or {}).get("sire") if isinstance(horse.get("pedigree"), dict) else None),
        ("damsire", (horse.get("pedigree") or {}).get("damsire") if isinstance(horse.get("pedigree"), dict) else None),
    ):
        txt = _s(value)
        if txt:
            out[f"category::{namespace}::{txt}"] = 1.0
    return out


def build_horse_features(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, float]:
    """Generate a sparse, leakage-conscious pre-race feature vector.

    The Cartesian expansion of metric × condition slice × lookback window × aggregate
    deliberately creates thousands of candidate features when enough historical data exists.
    Missing evidence is omitted instead of filled with fake neutral values.
    """
    ctx = _race_context(race)
    runs = _runs(horse, str(race.get("date") or ""))
    features = _static_features(horse, race)
    subsets = _filter_sets(runs, ctx)

    for subset_name, subset in subsets.items():
        if not subset:
            continue
        for window in WINDOWS:
            rows = subset if window is None else subset[:window]
            if not rows:
                continue
            wname = "all" if window is None else str(window)
            features[f"history::{subset_name}::w{wname}::run_count"] = float(len(rows))
            for metric_name, fn in RUN_METRICS.items():
                if metric_name == "clock_speed" and subset_name != "matched_clock_context":
                    continue
                stats = _aggregate_metric(rows, fn)
                for stat_name, value in stats.items():
                    features[f"history::{subset_name}::w{wname}::{metric_name}::{stat_name}"] = value

    # Cross-context deltas: useful for condition changes without hand-setting weights.
    anchors = (
        ("all", "same_track"),
        ("all", "same_surface"),
        ("all", "same_condition"),
        ("all", "distance_200"),
        ("same_surface", "same_surface_distance_200"),
        ("same_track", "same_track_distance_200"),
    )
    for left, right in anchors:
        for metric in ("finish_quality", "speed", "late_speed", "position_quality", "opponent_level"):
            lk = f"history::{left}::w5::{metric}::mean"
            rk = f"history::{right}::w5::{metric}::mean"
            if lk in features and rk in features:
                features[f"delta::{right}_minus_{left}::{metric}::w5"] = features[rk] - features[lk]

    return features


def _relative_percentile(values: list[float | None], value: float | None) -> float | None:
    valid = sorted(v for v in values if v is not None)
    if value is None or not valid:
        return None
    if len(valid) == 1:
        return 0.5
    less = sum(1 for x in valid if x < value)
    equal = sum(1 for x in valid if x == value)
    return (less + (equal - 1) / 2.0) / (len(valid) - 1)


def build_race_feature_matrix(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    """Build horse features and append race-relative transforms.

    For each numeric base feature, add percentile, z-score, field-mean delta and
    leader-gap. These transforms are often more useful than absolute values because
    race prediction is fundamentally comparative.
    """
    rows = [
        {"horse": horse, "features": build_horse_features(horse, race)}
        for horse in horses
        if isinstance(horse, dict)
    ]
    keys = sorted({k for row in rows for k in row["features"] if not k.startswith("category::")})

    for key in keys:
        vals = [_f(row["features"].get(key)) for row in rows]
        valid = [v for v in vals if v is not None]
        if not valid:
            continue
        m = sum(valid) / len(valid)
        sd = _std(valid) or 0.0
        best = max(valid)
        for row, value in zip(rows, vals):
            if value is None:
                continue
            pct = _relative_percentile(vals, value)
            if pct is not None:
                row["features"][f"relative::{key}::percentile"] = pct
            row["features"][f"relative::{key}::field_mean_delta"] = value - m
            row["features"][f"relative::{key}::leader_gap"] = best - value
            if sd > 0:
                row["features"][f"relative::{key}::zscore"] = (value - m) / sd

    for row in rows:
        row["featureCount"] = len(row["features"])
        row["schemaVersion"] = FEATURE_SCHEMA_VERSION
    return rows


def feature_schema_summary(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    names = sorted({name for row in matrix for name in (row.get("features") or {})})
    return {
        "schemaVersion": FEATURE_SCHEMA_VERSION,
        "horseCount": len(matrix),
        "featureCount": len(names),
        "marketFeatureCount": sum(name.startswith("market::") for name in names),
        "categoryFeatureCount": sum(name.startswith("category::") for name in names),
        "relativeFeatureCount": sum(name.startswith("relative::") for name in names),
        "historyFeatureCount": sum(name.startswith("history::") for name in names),
        "featureNames": names,
    }
