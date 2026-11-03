"""Shadow lane v9: probability post-processing on top of the v8
candidate (Elo + speed v2), built for forward validation.

The v9 lane changes NOTHING about ability, Elo, speed or features.
It post-processes the v8 win probabilities only, attacking the two
weaknesses measured on the graded v8 forward seals (190 pairs,
2026-10-29..2026-11-01, scoreboard of 2026-11-02):

1. Calibration: v8 assigned the actual winner on average only
   16.5% probability (the market assigned ~25%). Arm A (v9a)
   applies temperature scaling (one scalar T on the
   log-probabilities, fitted once by minimizing logloss on the
   graded v8 seals, then frozen) to sharpen the distribution.
2. Pool selection: of the winners outside v8's five marks, ~70%
   were in the market's top five by win odds. Arm B (v9b) blends
   the calibrated probabilities with the market-implied win
   probabilities from seal-time win odds (geometric / log-opinion
   pool, fixed preregistered weight 0.5). Races without usable
   seal-time odds fall back to the calibrated model probabilities
   for that race; the fallback is recorded per race in the sealed
   payload.

Marks and tickets derive from the post-processed probabilities
through the same downstream code as v8 (Plackett-Luce marginals
over the effective strengths, the shared marks assignment, and
generate_tickets, which reads the runner strengths — so each v9
runner's recorded strength IS the effective strength that
generates its probabilities).

Preregistration: goals/arvexq/hidden_files/
shadow-v9-preregistration-20261102.md. The lane seals only its own
store (var/seals/sealed_shadow_v9.sqlite3) and only races dated on
or after LANE_START_DATE. Production is untouched unless this lane
proves out on its own forward seals and the user approves.
"""
from __future__ import annotations

from math import fsum
from typing import Optional

from ..safety.probability import distribution, marginals
from .forecast import (
    PROBABILITY_STATUS,
    RaceForecast,
    RunnerForecast,
    _assign_marks,
)
from .shadow_v8 import MODEL_KEY as BASE_MODEL_KEY

# Fitted once at build time on the graded v8 forward seals and
# frozen for the lane's first sealing period. Fit set: the 190 v8
# seals with known results at build time (2026-10-29..2026-11-01);
# one race (jra-2026-10-31-東京-02) is excluded from the logloss
# fit because its winner was outside the sealed runner set (the
# roster grew after the seal-time snapshot). v8 raw logloss on the
# fit set 1.9729 -> 1.9299 at this T.
TEMPERATURE = 0.6692
TEMPERATURE_FIT = {
    "fittedOn": "graded-v8-forward-seals",
    "races": 190,
    "loglossRaces": 189,
    "dateFrom": "2026-10-29",
    "dateTo": "2026-11-01",
    "loglossV8Raw": 1.9729,
    "loglossV9aAtFit": 1.9299,
}
BLEND_WEIGHT = 0.5
LANE_START_DATE = "2026-11-04"

MODEL_KEY_A = "arvexq-shadow-v9a-elo-speed2-temp0.6692-natkey1"
MODEL_KEY_B = "arvexq-shadow-v9b-elo-speed2-temp0.6692-blend50-natkey1"
MODEL_VERSION_A = "arvexq-shadow-v9a-candidate"
MODEL_VERSION_B = "arvexq-shadow-v9b-candidate"

ARMS = {
    "v9a": {"model_key": MODEL_KEY_A, "model_version": MODEL_VERSION_A},
    "v9b": {"model_key": MODEL_KEY_B, "model_version": MODEL_VERSION_B},
}


def temperature_probs(probs: dict[int, float],
                      temperature: float) -> dict[int, float]:
    """Temperature scaling: q_n ∝ p_n ** (1/T), renormalized.
    T < 1 sharpens (the v8 fit is underconfident, so T < 1)."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    scaled = {n: (p ** (1.0 / temperature)) if p > 0 else 0.0
              for n, p in probs.items()}
    total = fsum(scaled.values())
    if total <= 0:
        raise ValueError("degenerate probability vector")
    return {n: v / total for n, v in scaled.items()}


def usable_market(win_odds: dict[int, float],
                  numbers) -> bool:
    """Seal-time odds are usable for the blend only when every
    runner in the probability vector carries a real win odd
    (> 1.0). Partial coverage falls back to model-only for the
    whole race — no imputation."""
    return all(
        isinstance(win_odds.get(n), (int, float))
        and not isinstance(win_odds.get(n), bool)
        and win_odds[n] > 1.0
        for n in numbers
    )


def market_probs(win_odds: dict[int, float],
                 numbers) -> dict[int, float]:
    """Market-implied win probabilities: inverse odds, normalized
    (the overround is distributed proportionally)."""
    inv = {n: 1.0 / float(win_odds[n]) for n in numbers}
    total = fsum(inv.values())
    return {n: v / total for n, v in inv.items()}


def blend_probs(calibrated: dict[int, float],
                market: dict[int, float],
                weight: float = BLEND_WEIGHT) -> dict[int, float]:
    """Geometric (log-opinion) pool: q_n ∝ p_n^(1-w) * m_n^w."""
    if not 0.0 <= weight <= 1.0:
        raise ValueError("blend weight outside [0, 1]")
    pooled = {n: calibrated[n] ** (1.0 - weight) * market[n] ** weight
              for n in calibrated}
    total = fsum(pooled.values())
    if total <= 0:
        raise ValueError("degenerate blend")
    return {n: v / total for n, v in pooled.items()}


def postprocess_forecast(
    forecast: RaceForecast,
    *,
    arm: str,
    win_odds: Optional[dict[int, float]] = None,
    temperature: float = TEMPERATURE,
) -> tuple[RaceForecast, dict]:
    """Build one v9 arm's forecast from a v8 RaceForecast.

    Returns (forecast, info); info records whether the market
    blend applied (arm v9b) for the sealed payload. Forecasts
    without a usable probability vector (status != "ok") pass
    through unchanged, exactly as the v8 lane seals them.
    """
    if arm not in ARMS:
        raise ValueError(f"unknown v9 arm: {arm}")
    info = {"arm": arm, "temperature": temperature,
            "blendWeight": BLEND_WEIGHT if arm == "v9b" else None,
            "blendApplied": False}
    if forecast.status != "ok":
        info["passthrough"] = forecast.status
        return forecast, info
    strengths = {r.number: r.strength for r in forecast.runners
                 if r.strength is not None and r.strength > 0}
    if len(strengths) < 3:
        info["passthrough"] = "insufficient-strengths"
        return forecast, info
    # PL win probabilities are proportional to strengths, so the
    # temperature acts on the strengths identically.
    base = {n: s / fsum(strengths.values())
            for n, s in strengths.items()}
    final = temperature_probs(base, temperature)
    if arm == "v9b" and win_odds and usable_market(win_odds, base):
        final = blend_probs(final, market_probs(win_odds, base))
        info["blendApplied"] = True
    # The final win probabilities ARE the effective PL strengths
    # (win marginal = s / sum(s), and they already sum to 1), so
    # marginals and tickets downstream stay consistent.
    probs = marginals(distribution(dict(final)))
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranked, probs)
    runners = []
    for r in forecast.runners:
        if r.number in probs:
            runners.append(RunnerForecast(
                number=r.number, name=r.name,
                ability_score=r.ability_score,
                strength=round(final[r.number], 6),
                pace_adjustment=r.pace_adjustment,
                pace_reasons=r.pace_reasons,
                p_win=round(probs[r.number][0], 4),
                p_top2=round(probs[r.number][1], 4),
                p_top3=round(probs[r.number][2], 4),
                mark=marks.get(r.number, ""),
                status=r.status,
            ))
        else:
            runners.append(r)
    return RaceForecast(forecast.race_id, forecast.beta,
                        PROBABILITY_STATUS, tuple(runners), "ok"), info
