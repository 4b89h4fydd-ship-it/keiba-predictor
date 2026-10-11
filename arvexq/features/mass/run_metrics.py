"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

from math import sqrt
from typing import Any, Iterable
from arvexq.prediction.jra_class_evidence import class_ordinal


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

