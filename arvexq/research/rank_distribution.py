"""Exact Plackett-Luce research distribution, NOT an empirically validated model.

Strengths must come from a separately trained, temporally validated estimator.
This module proves probability bookkeeping only; it does not infer ability,
invent scenario likelihoods or certify calibration. No production caller.
"""
from __future__ import annotations
import itertools
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RankDistribution:
    runners: tuple[int, ...]
    marginals: tuple[tuple[float, ...], ...]  # horse x position
    podium: dict[tuple[int, ...], float]  # disjoint ordered outcomes
    calibrated: bool = False

    def ticket_probability(self, kind: str, combos: list[list[int]]) -> float:
        sizes = {"単勝": 1, "馬単": 2, "馬連": 2, "ワイド": 2, "3連複": 3, "3連単": 3}
        if kind not in sizes:
            raise ValueError("unsupported ticket kind")
        size = sizes[kind]
        if size > len(self.runners):
            raise ValueError("not enough runners for ticket")
        selections = set()
        for combo in combos:
            c = tuple(combo)
            if len(c) != size or len(set(c)) != size or not set(c).issubset(self.runners):
                raise ValueError("invalid or inactive runner combination")
            selections.add(c if kind in ("単勝", "馬単", "3連単") else tuple(sorted(c)))
        total = []
        for order, p in self.podium.items():
            if kind == "ワイド":
                hit = any(set(c).issubset(order) for c in selections)
            else:
                outcome = order[:size]
                if kind in ("馬連", "3連複"):
                    outcome = tuple(sorted(outcome))
                hit = outcome in selections
            if hit:
                total.append(p)
        # A union of disjoint race outcomes, not a sum of overlapping ticket hits.
        return math.fsum(total)


def ranking_distribution(strengths: dict[int, float]) -> RankDistribution:
    if not strengths or len(strengths) > 18:
        raise ValueError("exact research distribution supports 1 to 18 active runners")
    if any(type(no) is not int or no <= 0 for no in strengths):
        raise ValueError("runner IDs must be positive integers")
    if any(not math.isfinite(w) or w <= 0 for w in strengths.values()):
        raise ValueError("strengths must be finite and strictly positive")
    nos = tuple(sorted(strengths))
    scale = max(strengths.values())
    weights = [strengths[no]/scale for no in nos]
    if any(w == 0 for w in weights):
        raise ValueError("strength ratio underflows; use a numerically bounded trained model")
    n = len(nos)
    full = (1 << n)-1
    mass = [0.0]*(1 << n)
    mass[0] = 1.0
    marginal = [[0.0]*n for _ in nos]
    for mask in range(full):
        rank = mask.bit_count()
        remaining = [i for i in range(n) if not mask & (1 << i)]
        total = math.fsum(weights[i] for i in remaining)
        for i in remaining:
            transition = mass[mask]*weights[i]/total
            mass[mask | (1 << i)] += transition
            marginal[i][rank] += transition
    podium = {}
    for indexes in itertools.permutations(range(n), min(3, n)):
        remaining = set(range(n))
        probability = 1.0
        for i in indexes:
            probability *= weights[i]/math.fsum(weights[j] for j in remaining)
            remaining.remove(i)
        podium[tuple(nos[i] for i in indexes)] = probability
    return RankDistribution(nos, tuple(tuple(row) for row in marginal), podium)


def mix_scenarios(scenarios: list[tuple[float, RankDistribution]]) -> RankDistribution:
    if not scenarios or any(not math.isfinite(p) or p < 0 for p, _ in scenarios):
        raise ValueError("invalid scenario probabilities")
    if abs(math.fsum(p for p, _ in scenarios)-1) > 1e-12:
        raise ValueError("scenario probabilities must already sum to one")
    nos = scenarios[0][1].runners
    if any(d.runners != nos for _, d in scenarios):
        raise ValueError("scenario runner sets must match exactly")
    n = len(nos)
    marginal = tuple(tuple(math.fsum(p*d.marginals[i][j] for p, d in scenarios)
                           for j in range(n)) for i in range(n))
    outcomes = scenarios[0][1].podium
    podium = {order: math.fsum(p*d.podium[order] for p, d in scenarios) for order in outcomes}
    return RankDistribution(nos, marginal, podium)
