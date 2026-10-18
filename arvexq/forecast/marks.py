"""116: Pure, fail-closed five-symbol marks from an approved probability forecast.

This module does not activate a model. A production forecast adapter must
explicitly attest that its pre-race probabilities passed the release gate.
"""
from __future__ import annotations

import math


def _probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) and 0.0 <= value <= 1.0 else None


def generate_marks(prediction):
    """Return [{horseNumber, mark}] or [] when the forecast is not releasable.

    Input contract:
      {"approvedForProduction": True,
       "horses": [{"horseNumber": 1, "winProbability": 0.2,
                   "top3Probability": 0.5}, ...]}

    Only the separately verified forecast adapter may authorize release.
    Duplicate horse numbers, missing/inconsistent probabilities and incomplete
    first-place probability mass fail closed. No odds or past results are used.
    """
    if not isinstance(prediction, dict) or prediction.get("approvedForProduction") is not True:
        return []
    horses = prediction.get("horses")
    if not isinstance(horses, list) or len(horses) < 2:
        return []

    parsed = []
    numbers = set()
    for horse in horses:
        if not isinstance(horse, dict):
            return []
        number = horse.get("horseNumber")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0 or number in numbers:
            return []
        win = _probability(horse.get("winProbability"))
        top3 = _probability(horse.get("top3Probability"))
        if win is None or top3 is None or top3 + 1e-9 < win:
            return []
        numbers.add(number)
        parsed.append((number, win, top3))
    if not 0.99 <= sum(row[1] for row in parsed) <= 1.01:
        return []

    # 1st-place accuracy wins ties; podium probability breaks remaining ties.
    ranked = sorted(parsed, key=lambda row: (-row[1], -row[2], row[0]))
    marks = ("◎", "○", "▲", "△", "☆")
    return [{"horseNumber": row[0], "mark": marks[i]} for i, row in enumerate(ranked[:5])]


def clear_marks(detail):
    """Remove obsolete prediction artifacts while preserving observed facts."""
    if not isinstance(detail, dict):
        return detail
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        for key in ("integratedEvaluation", "mark", "predMark", "honmeiRole", "modelProbabilities"):
            horse.pop(key, None)
    for key in ("factorRanking", "honmeiDecision", "markMethod", "observedModelCoverage"):
        detail.pop(key, None)
    return detail
