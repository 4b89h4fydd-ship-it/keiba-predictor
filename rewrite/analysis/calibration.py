"""Calibration evaluation and temperature fitting, time-split safe.

A labelled race is (date, {number: p_win}, winner_number, top3_numbers).
Fitting (choosing beta) is allowed ONLY on a training slice whose dates
are strictly earlier than every evaluation date; any overlap raises.
Metrics: log loss and Brier score on win probabilities, reliability
buckets, and top-3 hit accounting for the ◎ selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable, Optional

EPS = 1e-12


@dataclass(frozen=True)
class LabelledRace:
    date: str
    p_win: dict
    winner: int
    top3: tuple


def _check_split(train: list[LabelledRace], test: list[LabelledRace]) -> None:
    if train and test and max(r.date for r in train) >= min(r.date for r in test):
        raise ValueError("time split violated: train dates must precede test dates")


def log_loss(races: Iterable[LabelledRace]) -> float:
    races = list(races)
    if not races:
        raise ValueError("no races")
    total = 0.0
    for race in races:
        p = race.p_win.get(race.winner)
        if p is None:
            raise ValueError("winner missing from probabilities")
        total += -log(max(p, EPS))
    return total / len(races)


def brier(races: Iterable[LabelledRace]) -> float:
    races = list(races)
    if not races:
        raise ValueError("no races")
    total = 0.0
    for race in races:
        total += sum(
            (p - (1.0 if n == race.winner else 0.0)) ** 2
            for n, p in race.p_win.items()
        )
    return total / len(races)


def reliability(races: Iterable[LabelledRace], buckets: int = 10) -> list[dict]:
    counts = [0] * buckets
    wins = [0] * buckets
    prob_sums = [0.0] * buckets
    for race in races:
        for n, p in race.p_win.items():
            index = min(int(p * buckets), buckets - 1)
            counts[index] += 1
            prob_sums[index] += p
            wins[index] += 1 if n == race.winner else 0
    return [
        {
            "bucket": f"{i / buckets:.1f}-{(i + 1) / buckets:.1f}",
            "count": counts[i],
            "mean_probability": (prob_sums[i] / counts[i]) if counts[i] else None,
            "win_rate": (wins[i] / counts[i]) if counts[i] else None,
        }
        for i in range(buckets)
    ]


def honmei_record(races: Iterable[LabelledRace]) -> dict:
    """◎ (top-probability pick) outcomes: win rate and top-3 rate."""
    races = list(races)
    wins = top3 = counted = 0
    for race in races:
        pick = max(race.p_win, key=lambda n: (race.p_win[n], -n)) if race.p_win else None
        if pick is None:
            continue
        counted += 1
        wins += 1 if pick == race.winner else 0
        top3 += 1 if pick in race.top3 else 0
    return {
        "races": counted,
        "honmei_win_rate": (wins / counted) if counted else None,
        "honmei_top3_rate": (top3 / counted) if counted else None,
    }


def fit_beta(
    train: list[LabelledRace],
    strength_fn,
    candidates: Iterable[float],
    test: Optional[list[LabelledRace]] = None,
) -> dict:
    """Grid-search the strength temperature on the training slice only.

    ``strength_fn(beta, race_like) -> {number: p_win}`` is supplied by
    the caller (it re-runs the forecast at a given beta). When ``test``
    is given, the split is validated and test metrics are reported for
    the chosen beta — never used for selection.
    """
    if test:
        _check_split(train, test)
    scored = []
    for beta in candidates:
        rebuilt = [
            LabelledRace(r.date, strength_fn(beta, r), r.winner, r.top3) for r in train
        ]
        scored.append((log_loss(rebuilt), beta))
    scored.sort()
    best_loss, best_beta = scored[0]
    result = {"beta": best_beta, "train_log_loss": best_loss, "candidates": len(scored)}
    if test:
        rebuilt_test = [
            LabelledRace(r.date, strength_fn(best_beta, r), r.winner, r.top3) for r in test
        ]
        result["test_log_loss"] = log_loss(rebuilt_test)
        result["test_brier"] = brier(rebuilt_test)
        result["test_honmei"] = honmei_record(rebuilt_test)
    return result
