"""Ticket generation and expected value, honesty-gated.

Probabilities for all seven ticket kinds come from the Plackett-Luce
distribution over the forecast strengths. Expected value is computed
ONLY where real odds exist:

- The production odds source currently publishes win odds only, so
  EV is possible for win tickets and nothing else. Other kinds carry
  ``odds_status="unavailable"`` and no EV figure is invented.
- While the probability layer is uncalibrated, EV *tickets* (the
  purchase-candidate lane) are suppressed entirely and the plan says
  why. Probability-ranked tickets are still produced, explicitly
  labelled uncalibrated.
- Separately, per-horse win EV *estimates* (model win probability x
  real win odds) are exposed for display, always labelled as
  uncalibrated estimates; they never enter the EV ticket lane and
  carry no stake sizing.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations
from math import isfinite
from typing import Optional

from ..safety.probability import distribution, expected_return, ticket_probability
from .forecast import RaceForecast

KINDS = ("win", "place", "wide", "quinella", "exacta", "trio", "trifecta")


@dataclass(frozen=True)
class TicketPolicy:
    max_points: dict = None
    min_probability: dict = None

    def __post_init__(self):
        if self.max_points is None:
            object.__setattr__(self, "max_points", {
                "win": 1, "place": 3, "wide": 6, "quinella": 6,
                "exacta": 6, "trio": 10, "trifecta": 12,
            })
        if self.min_probability is None:
            object.__setattr__(self, "min_probability", {
                "win": 0.05, "place": 0.20, "wide": 0.05, "quinella": 0.03,
                "exacta": 0.02, "trio": 0.01, "trifecta": 0.005,
            })


@dataclass(frozen=True)
class Ticket:
    kind: str
    selection: tuple
    probability: float
    odds: Optional[float]
    expected_return: Optional[float]
    lane: str  # "ev" | "probability"
    odds_status: str  # "actual" | "unavailable"
    stake_units: Optional[float]


@dataclass(frozen=True)
class TicketPlan:
    race_id: str
    ev_tickets: tuple
    probability_tickets: tuple
    suppressed: dict  # reason -> count or explanation
    # Display-only win EV estimates (lane="ev-estimate"), one per
    # runner with real win odds. Never purchase candidates.
    win_ev_estimates: tuple = ()


def _candidates(forecast: RaceForecast, kind: str, ranked: list[int]) -> list[tuple]:
    top = {k: ranked[:n] for k, n in
           (("w", 4), ("x", 3), ("t", 5))}
    if kind == "win":
        return [(n,) for n in ranked[:2]]
    if kind == "place":
        by_top3 = sorted(
            (r for r in forecast.runners if r.p_top3 is not None),
            key=lambda r: (-r.p_top3, r.number),
        )
        return [(r.number,) for r in by_top3[:4]]
    if kind in ("wide", "quinella"):
        return list(combinations(top["w"], 2))
    if kind == "exacta":
        return list(permutations(top["x"], 2))
    if kind == "trio":
        return list(combinations(top["t"], 3))
    if kind == "trifecta":
        return list(permutations(top["w"][:4], 3))
    return []


def generate_tickets(
    forecast: RaceForecast,
    win_odds: dict[int, float],
    *,
    calibration_validated: bool,
    policy: Optional[TicketPolicy] = None,
) -> TicketPlan:
    policy = policy or TicketPolicy()
    if forecast.status != "ok":
        return TicketPlan(forecast.race_id, (), (), {
            "forecast": forecast.status,
        })
    strengths = {
        r.number: r.strength for r in forecast.runners if r.strength is not None
    }
    outcomes = distribution(strengths)
    ranked = sorted(
        strengths,
        key=lambda n: (
            -(next(r.p_win for r in forecast.runners if r.number == n) or 0.0), n
        ),
    )
    probability_tickets: list[Ticket] = []
    ev_tickets: list[Ticket] = []
    suppressed: dict[str, int] = {}
    for kind in KINDS:
        scored: list[Ticket] = []
        for selection in _candidates(forecast, kind, ranked):
            p = ticket_probability(outcomes, kind, selection)
            if p < policy.min_probability[kind]:
                continue
            odds = win_odds.get(selection[0]) if kind == "win" else None
            odds_status = "actual" if odds is not None else "unavailable"
            scored.append(Ticket(
                kind=kind, selection=selection, probability=round(p, 4),
                odds=odds, expected_return=None, lane="probability",
                odds_status=odds_status, stake_units=None,
            ))
        scored.sort(key=lambda t: (-t.probability, t.selection))
        kept = scored[: policy.max_points[kind]]
        probability_tickets.extend(kept)
        if kind != "win":
            if kept:
                suppressed[f"ev_{kind}"] = "odds-unavailable"
            continue
        # Win EV lane: real odds exist; calibration gate decides.
        for ticket in kept:
            if ticket.odds is None:
                suppressed["ev_win"] = "odds-unavailable"
                continue
            try:
                value = expected_return(
                    ticket.probability, ticket.odds, validated=calibration_validated
                )
            except ValueError:
                suppressed["ev_win"] = "calibration-not-validated"
                continue
            if value <= 1.0:
                suppressed["ev_win_below_1"] = suppressed.get("ev_win_below_1", 0) + 1
                continue
            kelly = (value - 1.0) / (ticket.odds - 1.0) if ticket.odds > 1 else 0.0
            ev_tickets.append(Ticket(
                kind="win", selection=ticket.selection,
                probability=ticket.probability, odds=ticket.odds,
                expected_return=round(value, 4), lane="ev",
                odds_status="actual",
                stake_units=round(min(kelly, 0.05), 4),
            ))
    # Display-only win EV estimates: model win probability x real win
    # odds for EVERY runner that has real odds, regardless of the
    # calibration gate above. These are uncalibrated estimates for
    # display; the EV ticket lane stays gated on validated
    # calibration, and no stake sizing is attached here.
    estimates: list[Ticket] = []
    for runner in forecast.runners:
        if runner.p_win is None:
            continue
        raw_odds = win_odds.get(runner.number)
        if raw_odds is None:
            continue
        try:
            odds_value = float(raw_odds)
        except (TypeError, ValueError):
            continue
        if not isfinite(odds_value) or odds_value < 1:
            continue
        estimates.append(Ticket(
            kind="win", selection=(runner.number,),
            probability=round(runner.p_win, 4), odds=odds_value,
            expected_return=round(runner.p_win * odds_value, 4),
            lane="ev-estimate", odds_status="actual", stake_units=None,
        ))
    estimates.sort(key=lambda t: (-(t.expected_return or 0.0), t.selection))
    return TicketPlan(
        race_id=forecast.race_id,
        ev_tickets=tuple(ev_tickets),
        probability_tickets=tuple(probability_tickets),
        suppressed=suppressed,
        win_ev_estimates=tuple(estimates),
    )
