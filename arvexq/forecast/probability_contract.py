"""Research-to-production boundary: validate probability mathematics, never approve deployment.

Input is the model's pre-race ordered top-3 joint distribution. Returns
horse-level win/top-three probabilities derived from that SAME joint forecast.
A valid distribution is necessary, never sufficient, for production approval.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import permutations
import math


def summarize_joint_top3(rows, runner_numbers):
    """Return normalized model summary or None for incomplete/inconsistent data.

    runner_numbers: full official starter list (>=3 unique positive integers).
    rows: complete ordered triples with their probabilities (zeros permitted).
    Every ordered triple must occur exactly once: partial distributions cannot
    be mistaken for full event space. No model authorization is set here.
    """
    if not isinstance(runner_numbers, (list, tuple)) or len(runner_numbers) < 3:
        return None
    if any(type(n) is not int or n <= 0 for n in runner_numbers) or len(set(runner_numbers)) != len(runner_numbers):
        return None
    n = len(runner_numbers)
    expected = n * (n - 1) * (n - 2)
    if not isinstance(rows, list) or len(rows) != expected:
        return None
    runner_set = set(runner_numbers)
    observed = set()
    win = defaultdict(float)
    top3 = defaultdict(float)
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            return None
        numbers = row.get("horseNumbers")
        p = row.get("probability")
        if (not isinstance(numbers, (list, tuple)) or len(numbers) != 3
                or any(type(x) is not int or x not in runner_set for x in numbers)
                or len(set(numbers)) != 3 or isinstance(p, bool)
                or not isinstance(p, (int, float))):
            return None
        p = float(p)
        if not math.isfinite(p) or not 0.0 <= p <= 1.0:
            return None
        key = tuple(numbers)
        if key in observed:
            return None
        observed.add(key)
        total += p
        win[key[0]] += p
        for number in key:
            top3[number] += p
    if not 0.999999 <= total <= 1.000001:
        return None
    return {"horses": [
        {"horseNumber": number, "winProbability": win[number] / total,
         "top3Probability": top3[number] / total}
        for number in sorted(runner_set)
    ], "orderedTop3": rows}
