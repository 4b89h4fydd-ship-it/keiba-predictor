"""Read-only, pre-race held-out validation metrics for the new B forecast.

This module evaluates saved predictions against observed results; it never
generates live forecasts, changes marks, or authorizes a production release.
"""
from __future__ import annotations

from collections import defaultdict
import math


def evaluate_race(ordered_top3, finish_order, *, prediction_cutoff, off_time):
    """Score an exhaustive model forecast against a settled result.

    ordered_top3 is [{horseNumbers:[first,second,third],probability:float}].
    finish_order contains every official starter in finish order (no dead heats).
    Timestamp strings must be timezone-aware ISO 8601 and prediction_cutoff
    must precede off_time. Returns None for any invalid/unsafe record.
    """
    from datetime import datetime
    try:
        prediction_time = datetime.fromisoformat(prediction_cutoff)
        race_time = datetime.fromisoformat(off_time)
        if (prediction_time.tzinfo is None or race_time.tzinfo is None
                or prediction_time >= race_time):
            return None
    except (TypeError, ValueError):
        return None
    if (not isinstance(finish_order, list) or len(finish_order) < 3
            or any(type(n) is not int or n <= 0 for n in finish_order)
            or len(finish_order) != len(set(finish_order))):
        return None
    n = len(finish_order)
    expected = n * (n - 1) * (n - 2)
    if not isinstance(ordered_top3, list) or len(ordered_top3) != expected:
        return None
    runners = set(finish_order)
    joint = {}
    win = defaultdict(float)
    podium = defaultdict(float)
    total = 0.0
    for row in ordered_top3:
        if not isinstance(row, dict):
            return None
        trio = row.get("horseNumbers")
        p = row.get("probability")
        if (not isinstance(trio, (list, tuple)) or len(trio) != 3
                or len(set(trio)) != 3 or any(type(x) is not int or x not in runners for x in trio)
                or isinstance(p, bool) or not isinstance(p, (int, float))):
            return None
        p = float(p)
        if not math.isfinite(p) or not 0 <= p <= 1:
            return None
        key = tuple(trio)
        if key in joint:
            return None
        joint[key] = p
        win[key[0]] += p
        for number in key:
            podium[number] += p
        total += p
    if not 0.999999 <= total <= 1.000001:
        return None
    winner = finish_order[0]
    observed = tuple(finish_order[:3])
    rank_win = sorted(finish_order, key=lambda number: (-win[number], number))
    rank_podium = sorted(finish_order, key=lambda number: (-podium[number], number))
    epsilon = 1e-15
    return {
        "winTop1Hit": int(rank_win[0] == winner),
        "winLogLoss": -math.log(max(win[winner] / total, epsilon)),
        "orderedTop3Hit": int(max(joint, key=lambda x: (joint[x], tuple(-v for v in x))) == observed),
        "orderedTop3LogLoss": -math.log(max(joint[observed] / total, epsilon)),
        "top3SetHit": int(set(rank_podium[:3]) == set(observed)),
        "top3Recall": len(set(rank_podium[:3]) & set(observed)) / 3,
        "observedWinnerProbability": win[winner] / total,
        "observedOrderProbability": joint[observed] / total,
    }


def summarize_results(scored_races):
    """Macro averages across valid races; an empty/invalid sample never passes."""
    if not isinstance(scored_races, list) or not scored_races:
        return None
    names = ("winTop1Hit", "winLogLoss", "orderedTop3Hit", "orderedTop3LogLoss",
             "top3SetHit", "top3Recall")
    for row in scored_races:
        if not isinstance(row, dict) or any(
            not isinstance(row.get(k), (int, float)) or isinstance(row[k], bool)
            or not math.isfinite(row[k]) for k in names
        ):
            return None
    return {"raceCount": len(scored_races), **{
        key: sum(row[key] for row in scored_races) / len(scored_races)
        for key in names
    }}
