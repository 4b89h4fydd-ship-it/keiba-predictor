"""Exact top-three Plackett–Luce enumeration from externally validated strengths.

This is a distribution calculation, not a trained or calibrated model. Runtime
activation and expected-value claims require separate held-out evidence.
"""
from itertools import permutations
from math import fsum, isfinite


def distribution(strengths: dict[int, float]) -> dict[tuple[int, ...], float]:
    if len(strengths) < 2 or any(type(n) is not int or n < 1 for n in strengths):
        raise ValueError('invalid runner identities')
    if any(not isfinite(s) or s <= 0 for s in strengths.values()):
        raise ValueError('strengths must be positive and finite')
    scale = max(strengths.values())
    weights = {n: s / scale for n, s in strengths.items()}
    if any(s == 0 for s in weights.values()):
        raise ValueError('strength range exceeds numeric precision')
    outcomes = {}
    for order in permutations(weights, min(3, len(weights))):
        probability = 1.0
        remaining = set(weights)
        for n in order:
            probability *= weights[n] / fsum(weights[k] for k in remaining)
            remaining.remove(n)
        outcomes[order] = probability
    if abs(fsum(outcomes.values()) - 1) > 1e-10:
        raise ValueError('probability mass lost')
    return outcomes


def marginals(outcomes: dict[tuple[int, ...], float]) -> dict[int, tuple[float, float, float]]:
    runners = {n for order in outcomes for n in order}
    return {n: tuple(fsum(p for order, p in outcomes.items() if n in order[:k])
                     for k in (1, 2, 3)) for n in sorted(runners)}


def marks(outcomes: dict[tuple[int, ...], float]) -> dict[int, str]:
    values = marginals(outcomes)
    ranking = sorted(values, key=lambda n: (-values[n][0], -values[n][2], n))
    return {n: ('◎○▲△☆'[i] if i < 5 else '') for i, n in enumerate(ranking)}


def ticket_probability(outcomes: dict[tuple[int, ...], float], kind: str,
                       selection: tuple[int, ...], place_count: int = 3) -> float:
    sizes = {'win': 1, 'place': 1, 'wide': 2, 'quinella': 2,
             'exacta': 2, 'trio': 3, 'trifecta': 3}
    if kind not in sizes or len(selection) != sizes[kind] or len(set(selection)) != len(selection):
        raise ValueError('invalid ticket')
    runners = {n for order in outcomes for n in order}
    if not set(selection) <= runners or place_count not in (2, 3):
        raise ValueError('unknown runner or place rule')
    def wins(order):
        chosen = set(selection)
        if kind == 'win':
            return order[0] == selection[0]
        if kind == 'place':
            return selection[0] in order[:place_count]
        if kind == 'wide':
            return chosen <= set(order[:3])
        if kind in ('exacta', 'trifecta'):
            return order[:len(selection)] == selection
        return set(order[:len(selection)]) == chosen
    return fsum(p for order, p in outcomes.items() if wins(order))


def expected_return(probability: float, odds: float, *, validated: bool) -> float:
    if not validated:
        raise ValueError('held-out calibration and validation required')
    if not isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError('invalid probability')
    if not isfinite(odds) or odds < 1:
        raise ValueError('actual payout odds required')
    return probability * odds
