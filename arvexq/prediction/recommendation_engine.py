"""Deterministic recommendation layer; no network, odds fetching or model training.

Input is an out-of-sample, calibrated joint finishing-order distribution.
This module deliberately does not claim any hit-rate or profitability guarantee.
"""
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import isfinite

MARKS = ("◎", "○", "▲", "△", "☆")
SUPPORTED = ("win", "place", "wide", "quinella", "exacta", "trio", "trifecta")


@dataclass(frozen=True)
class Ticket:
    kind: str
    horses: tuple
    odds: float  # projected gross dividend per 1 unit of stake
    win_probability: float
    expected_return: float


def _validate_scenarios(scenarios):
    if not scenarios:
        raise ValueError("Scenarios must not be empty")
    total = 0.0
    field = None
    cleaned = []
    for order, probability in scenarios:
        order = tuple(str(h) for h in order)
        p = float(probability)
        if len(order) < 3 or len(set(order)) != len(order):
            raise ValueError("Each finishing order needs at least three distinct horses")
        if not isfinite(p) or p < 0:
            raise ValueError("Scenario probability must be finite and nonnegative")
        if field is None:
            field = set(order)
        if set(order) != field:
            raise ValueError("All scenarios must cover the same runners")
        total += p
        cleaned.append((order, p))
    if abs(total - 1.0) > 1e-6:
        raise ValueError("Joint probabilities must sum to one; never silently renormalize")
    return cleaned


def rank_marks(scenarios, max_lows=3, max_longshots=1):
    """Return simple marks; odds are intentionally excluded from ◎○▲ ranking."""
    rows = _validate_scenarios(scenarios)
    win, podium = defaultdict(float), defaultdict(float)
    for order, p in rows:
        win[order[0]] += p
        for h in order[:3]:
            podium[h] += p
    ranked = sorted(win, key=lambda h: (-win[h], -podium[h], h))
    # Include zero-win horses present in the field.
    ranked = sorted(podium, key=lambda h: (-win[h], -podium[h], h))
    marks = {}
    for symbol, horse in zip(MARKS[:3], ranked):
        marks[horse] = symbol
    remainder = sorted((h for h in podium if h not in marks),
                       key=lambda h: (-podium[h], h))
    for h in remainder[:max_lows]:
        marks[h] = "△"
    # ☆ is assigned only by an independently evaluated value signal, not invented here.
    return {"marks": marks, "win": dict(win), "top3": dict(podium),
            "unmarked": remainder[max_lows:]}


def _hit(kind, horses, order, place_payout_slots=3):
    top = order[:3]
    if kind == "win":
        return order[0] == horses[0]
    if kind == "place":
        return horses[0] in order[:place_payout_slots]
    if kind == "wide":
        return set(horses).issubset(set(order[:place_payout_slots]))
    if kind == "quinella":
        return set(horses) == set(order[:2])
    if kind == "exacta":
        return tuple(horses) == order[:2]
    if kind == "trio":
        return set(horses) == set(top)
    if kind == "trifecta":
        return tuple(horses) == top
    raise ValueError("Unsupported ticket type")


def evaluate_tickets(scenarios, quoted_odds, place_payout_slots=3):
    """Odds keys: (kind, (horse ids ...)); only explicitly quoted bets evaluated.

    Returns no betting proposals when odds are unavailable; never invent odds.
    place_payout_slots must reflect official race payout rules (2 or 3).
    """
    rows = _validate_scenarios(scenarios)
    if place_payout_slots not in (2, 3):
        raise ValueError("Invalid place payout slots")
    field = set(rows[0][0])
    results = []
    for (kind, horses), odds in quoted_odds.items():
        horses = tuple(str(h) for h in horses)
        if kind not in SUPPORTED or not horses or len(set(horses)) != len(horses):
            raise ValueError("Invalid ticket")
        if not set(horses).issubset(field):
            raise ValueError("Unknown horse")
        expected_length = {"win": 1, "place": 1, "wide": 2,
                           "quinella": 2, "exacta": 2, "trio": 3, "trifecta": 3}[kind]
        if len(horses) != expected_length:
            raise ValueError("Wrong ticket size")
        odds = float(odds)
        if not isfinite(odds) or odds <= 0:
            raise ValueError("Odds must be positive and finite")
        p = sum(prob for order, prob in rows
                if _hit(kind, horses, order, place_payout_slots))
        results.append(Ticket(kind, horses, odds, p, p * odds))
    return sorted(results, key=lambda t: (-t.expected_return, -t.win_probability, t.kind, t.horses))


def recommend(scenarios, quoted_odds, max_tickets=6, min_expected_return=1.0,
              min_hit_probability=0.8, place_payout_slots=3):
    """Search small portfolios with 1 unit/ticket; refuse negative-EV bets.

    Objective: among portfolios meeting target joint-hit probability choose
    highest expected return, breaking ties for fewer tickets. If no portfolio
    meets the threshold return no recommendation, never fabricate attainment.
    """
    if not 1 <= max_tickets <= 12:
        raise ValueError("max_tickets outside safe range")
    rows = _validate_scenarios(scenarios)
    ranked = [t for t in evaluate_tickets(rows, quoted_odds, place_payout_slots)
              if t.expected_return >= min_expected_return]
    # Bound combinatorial work. These are candidate tickets, not an exhaustive
    # global optimum when more than 18 positive-EV opportunities exist.
    ranked = ranked[:18]
    best = None
    for k in range(1, min(max_tickets, len(ranked)) + 1):
        for pool in combinations(ranked, k):
            hit = sum(p for order, p in rows
                      if any(_hit(t.kind, t.horses, order, place_payout_slots)
                             for t in pool))
            if hit + 1e-12 < min_hit_probability:
                continue
            roi = sum(t.expected_return for t in pool) / len(pool)
            candidate = (roi, -len(pool), hit, pool)
            if best is None or candidate[:3] > best[:3]:
                best = candidate
    if best is None:
        return {"status": "no_recommendation", "reason": "no_portfolio_meets_constraints",
                "tickets": [], "hit_probability": None, "expected_return": None}
    roi, _, hit, tickets = best
    return {"status": "recommended",
            "tickets": [{"kind": t.kind, "horses": list(t.horses),
                         "odds": t.odds, "hit_probability": t.win_probability,
                         "expected_return": t.expected_return} for t in tickets],
            "hit_probability": hit, "expected_return": roi,
            "assumptions": "Projected odds; equal stakes; calibrated scenarios required"}
