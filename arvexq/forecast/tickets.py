"""121: Independent probability-based ticket builder; no legacy fallbacks.

Requires a separately approved, exhaustive pre-race joint top-three distribution.
This function does NOT approve or install a prediction model.
"""
from __future__ import annotations

import math
from collections import defaultdict


def generate_tickets(prediction, marks):
    """Create one best-probability ticket each for 3連単, 3連複, 馬連.

    The input must include orderedTop3 entries with unique horseNumbers and
    normalized joint probabilities. The returned probabilities are event
    probabilities, NOT expected returns or guaranteed hit rates. No stake or
    allocation is inferred without price/odds and validation.
    """
    if not isinstance(prediction, dict) or prediction.get("approvedForProduction") is not True:
        return []
    rows = prediction.get("orderedTop3")
    if not isinstance(rows, list) or not rows:
        return []
    if not isinstance(marks, list) or not marks:
        return []
    eligible = set()
    for mark in marks:
        if not isinstance(mark, dict):
            return []
        number = mark.get("horseNumber")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0 or number in eligible:
            return []
        if mark.get("mark") not in ("◎", "○", "▲", "△", "☆"):
            return []
        eligible.add(number)

    triple_probs = {}
    three_unordered = defaultdict(float)
    pair_probs = defaultdict(float)
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            return []
        numbers = row.get("horseNumbers")
        value = row.get("probability")
        if (not isinstance(numbers, (list, tuple)) or len(numbers) != 3
                or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in numbers)
                or len(set(numbers)) != 3
                or isinstance(value, bool) or not isinstance(value, (int, float))):
            return []
        probability = float(value)
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            return []
        key = tuple(numbers)
        if key in triple_probs:
            return []
        triple_probs[key] = probability
        three_unordered[tuple(sorted(key))] += probability
        pair_probs[tuple(sorted(key[:2]))] += probability
        total += probability
    # Missing permutations would distort the pair/combination marginals.
    if not 0.99 <= total <= 1.01:
        return []

    def best(data):
        candidates = [(p, key) for key, p in data.items() if p > 0 and all(n in eligible for n in key)]
        if not candidates:
            return None
        probability, key = sorted(candidates, key=lambda item: (-item[0], item[1]))[0]
        return {"horseNumbers": list(key), "probability": round(probability / total, 8)}

    tickets = []
    for bet_type, options in (("3連単", triple_probs), ("3連複", three_unordered), ("馬連", pair_probs)):
        pick = best(options)
        if pick is not None:
            tickets.append({"type": bet_type, **pick})
    return tickets
