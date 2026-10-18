"""Race-relative pace/closing context from already FROZEN pre-off history only.

No actual current pace, current corner order, odds, result or postrace fields.
Historical early-speed indexes are not assumed comparable across courses:
each evidence-based value is used ONLY as a within-field ordinal proxy.
An unavailable metric produces a missingness bit, never a guessed observation.
"""
from __future__ import annotations

from math import isfinite

VERSION = "arvexq-frozen-pace-context-research-v1"
NAMES = (
    "early_rank", "late_rank", "corner_rank",
    "front_competitors", "closing_vs_early",
    "early_missing", "late_missing", "corner_missing",
)
METRICS = {
    "early": "history::all::w5::early_speed::mean",
    "late": "history::all::w5::late_speed::mean",
    "corner": "history::all::w5::position_quality::mean",
}


def _observed(features, key):
    # Never coerce strings, booleans or postrace fields into model evidence.
    value = features.get(METRICS[key])
    count = features.get(METRICS[key].rsplit("::", 1)[0] + "::count")
    if (type(value) not in (int, float) or not isfinite(value)
            or type(count) not in (int, float) or not isfinite(count)
            or count < 2):
        return None
    return float(value)


def _percentiles(values):
    """Observed-only midrank, independent of runner-list ordering."""
    result = [None] * len(values)
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return result
    for i, value in enumerate(values):
        if value is not None:
            less = sum(x < value for x in present)
            equal = sum(x == value for x in present)
            result[i] = (less + (equal - 1) / 2) / (len(present) - 1)
    return result


def build_preoff_pace_context(race):
    """Return eight bounded features per runner, using only frozen history.

    Front competition measures other runners with a high observed early index;
    it is a pressure proxy, NOT the likelihood of an actual pace scenario.
    """
    horses = race.get("horses") if isinstance(race, dict) else None
    if not isinstance(horses, list) or not 3 <= len(horses) <= 24:
        raise ValueError("complete frozen runner field of 3-24 required")
    rows = []
    for horse in horses:
        if not isinstance(horse, dict) or not isinstance(horse.get("features"), dict):
            raise ValueError("frozen feature mapping required")
        rows.append(horse["features"])
    observed = {key: [_observed(row, key) for row in rows] for key in METRICS}
    ranks = {key: _percentiles(values) for key, values in observed.items()}
    candidates = [i for i, v in enumerate(ranks["early"]) if v is not None and v >= .70]
    out = []
    for i in range(len(rows)):
        early, late, corner = (ranks[k][i] for k in ("early", "late", "corner"))
        valid_early = early is not None
        # Count OTHER evidence-backed front-speed runners; no self-counting.
        others = sum(j != i for j in candidates)
        denom = max(1, len(rows)-1)
        values = (early if valid_early else 0.,
                  late if late is not None else 0.,
                  corner if corner is not None else 0.,
                  others / denom if valid_early else 0.,
                  (late - early) if valid_early and late is not None else 0.,
                  float(not valid_early),
                  float(late is None),
                  float(corner is None))
        if any(not isfinite(x) or abs(x) > 1 for x in values):
            raise ValueError("out of bounds pace context")
        out.append(list(values))
    return out
