"""Override guard: a final-stage correction on the v9b probability
vector, adopted 2026-11-27 by explicit user instruction ("なおせ").

Why it exists — the 2026-11-26 full audit (full-audit-20261126
part 1) measured the issued win probabilities against the market
on 180 production races (2026-11-21..26): the issued vector lost
to the market alone on both proper scores (Brier 0.0663 vs 0.0604,
LogLoss 0.2365 vs 0.2067), and in the 73 races where the model's
top pick overrode the favourite, the issued pick won 19.2% against
the displaced favourite's 30.1%. The override-guard simulation
(override-guard-sim-20261127) and its walk-forward re-check
(parameters selected on earlier days only, tested on later days,
135 races) both found the same fixed rule improves every headline
metric out of sample (LogLoss 0.2389 -> 0.2110, top-pick win rate
43.0% -> 46.7%):

  A (override replacement): when the model's top pick is not the
     favourite and its issued win probability exceeds the
     favourite's market-implied probability by less than
     MARGIN_THRESHOLD (0.15), replace the whole win vector with
     the market-implied vector. The overrides' margins are
     mostly negative (median -5.7pt on the audit corpus), so in
     practice this retires nearly every override; the threshold
     keeps only overrides the model backs by a wide margin.
  B (market regression): every race's win vector is then moved
     REGRESSION_LAMBDA (0.50) of the way toward the market-implied
     vector and renormalized. A race A replaced is already pure
     market, so B leaves it unchanged.
  C (market lean, override-guard-v2, adopted 2026-11-27 night by
     explicit user instruction after the day's issued card lost
     to the favourite again): the B output is geometrically
     pooled once more toward the market, q ∝ p^(1-w) * m^w with
     MARKET_LEAN_WEIGHT w = 0.30. Measured the same day on the
     issued vectors themselves (blend-lean-20261127: parameters
     read on 2026-11-24..25, 70 races, tested on 2026-11-26..27,
     82 races): leaning the issued vector by w = 0.25..0.5
     improved log-loss on BOTH halves (train 1.8380 -> 1.7633 at
     w = 0.4; test 1.7310 -> 1.6234) and the top-pick win rate
     (train 42.9% -> 44.3%; test 46.9% -> 51.9% at w = 0.25..0.4,
     the test half carrying a small odds-coverage quirk in two
     11-27 races), while the pure market (w = 1) was WORSE than
     the current vector on the train half (40.0% vs 42.9%) — the
     ability layer still adds something; the issued vector was
     simply under-anchored after the materials shifts. w = 0.30
     is the conservative middle of the measured band.
  D (netkeiba forecast lean, override-guard-v3, adopted
     2026-11-27 night by explicit user instruction "両方やる"
     after the beat-market search): the C output is geometrically
     pooled toward the vector implied by netkeiba's published
     FORECAST win odds (the materials file's per-horse
     forecastWin — a second market-style opinion, NOT the real
     market), q ∝ p^(1-w) * f^w with NK_FORECAST_LEAN_WEIGHT
     w = 0.30. The search (beat-market-search-20261127, 145
     races, weights read on 2026-11-24..25, tested on
     2026-11-26..27, reverse direction also checked) found this
     the strongest incremental signal over the v2 baseline:
     test log-loss -0.0631, top pick +3.9pt, and the leaned
     vector beat even the market-only vector on test log-loss
     (1.6827 vs 1.7133). The signal was already present in the
     lane as the weak +0.10 odds_forecast materials term; the
     measured dose is this final-stage lean. Step D fires only
     when forecast odds cover every runner in the vector
     (> 1.0 each); otherwise C's output stands. Jumps races
     never reach the guard, so D is v9b-lane only like A–C.

The market is built from the SAME win odds the v9b blend consumed
— the publisher's payload odds at compute time — never from final
odds: nothing post-off enters the guard. A race whose vector is
not fully covered by usable win odds (> 1.0 for every runner in
the vector) is not guarded at all: the issued vector stands and
info records why. No imputation.

The guard runs inside the publish build, after the v9b
post-processing and the nk-materials adjustment, through the same
Plackett-Luce rebuild shadow_v9.postprocess_forecast and
nk_materials.apply_nk_materials use, so marks, tickets, the
win/top-3 display and the master shadow all derive from the
guarded probabilities (one evaluation, no drift). It applies on
the v9b lane only: the audit corpus and both validations stand on
the blended v9b vector, and the unblended v1 vector (jumps) was
never measured under this rule.

The parameters are frozen constants of the adopted rule, not
fitted per race or per day — the walk-forward check selected
lambda = 0.50 on every test day. Changing them is a new adoption,
not a tuning knob.
"""

from __future__ import annotations

from math import fsum
from typing import Optional

from ..safety.probability import distribution, marginals
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .shadow_v9 import market_probs, usable_market

GUARD_VERSION = "override-guard-v3"

# Step A threshold (adopted rule, see module docstring): an
# override of the favourite is replaced by the market vector
# unless the model's top pick leads the favourite's market-implied
# probability by at least this much.
MARGIN_THRESHOLD = 0.15

# Step B regression weight (adopted rule, see module docstring):
# every guarded vector moves this fraction of the way toward the
# market-implied vector.
REGRESSION_LAMBDA = 0.50

# Step C market-lean weight (override-guard-v2, see module
# docstring): the step-B output is geometrically pooled toward
# the market with this weight.
MARKET_LEAN_WEIGHT = 0.30

# Step D netkeiba-forecast lean weight (override-guard-v3, see
# module docstring): the step-C output is geometrically pooled
# toward the netkeiba forecast-odds vector with this weight.
NK_FORECAST_LEAN_WEIGHT = 0.30


def _info() -> dict:
    return {"applied": False, "version": GUARD_VERSION,
            "marginThreshold": MARGIN_THRESHOLD,
            "regressionLambda": REGRESSION_LAMBDA,
            "marketLean": MARKET_LEAN_WEIGHT,
            "nkForecastLean": NK_FORECAST_LEAN_WEIGHT,
            "nkLeanApplied": False,
            "aFired": False, "modelPick": None, "favourite": None,
            "margin": None}


def guard_probabilities(probs: dict, win_odds: dict,
                        nk_forecast_odds: Optional[dict] = None):
    """The guard on a plain win-probability vector.

    ``probs`` is {horse number: issued win probability} (it need
    not be normalized; it is normalized here, exactly as the
    simulation normalized the sealed diagnosis vector).
    ``win_odds`` is {horse number: win odds} — the odds available
    at compute time.

    Returns (guarded, info); guarded is None when the market
    cannot be built for every runner in the vector — the guard
    does not fire then and the caller keeps the issued vector.
    The favourite is the market's own top horse (the lowest win
    odds, ties broken by horse number): at compute time no final
    popularity exists yet, and the market vector is the only
    market read the lane holds.
    """
    info = _info()
    numbers = sorted(probs)
    if len(numbers) < 3:
        info["reason"] = "insufficient-runners"
        return None, info
    total = fsum(probs[n] for n in numbers)
    if total <= 0:
        info["reason"] = "degenerate-vector"
        return None, info
    base = {n: probs[n] / total for n in numbers}
    if not win_odds or not usable_market(win_odds, numbers):
        info["reason"] = "market-incomplete"
        return None, info
    market = market_probs(win_odds, numbers)
    pick = min(numbers, key=lambda n: (-base[n], n))
    favourite = min(numbers, key=lambda n: (-market[n], n))
    margin = base[pick] - market[favourite]
    info.update({"modelPick": pick, "favourite": favourite,
                 "margin": margin})
    vector = base
    if pick != favourite and margin < MARGIN_THRESHOLD:
        vector = dict(market)
        info["aFired"] = True
    lam = REGRESSION_LAMBDA
    regressed = {n: (1.0 - lam) * vector[n] + lam * market[n]
                 for n in numbers}
    total = fsum(regressed.values())
    if total <= 0:
        info["reason"] = "degenerate-vector"
        return None, info
    regressed = {n: v / total for n, v in regressed.items()}
    # Step C (v2): geometric lean of the step-B output toward
    # the market. A pure-market vector (step A fired) is
    # unchanged by construction.
    w = MARKET_LEAN_WEIGHT
    leaned = {n: (regressed[n] ** (1.0 - w)) * (market[n] ** w)
              for n in numbers}
    total = fsum(leaned.values())
    if total <= 0:
        info["reason"] = "degenerate-vector"
        return None, info
    guarded = {n: v / total for n, v in leaned.items()}
    # Step D (v3): geometric lean toward the netkeiba forecast
    # vector, only on full forecast-odds coverage of the vector.
    if nk_forecast_odds and usable_market(nk_forecast_odds,
                                          numbers):
        nk_vector = market_probs(nk_forecast_odds, numbers)
        wd = NK_FORECAST_LEAN_WEIGHT
        leaned_d = {n: (guarded[n] ** (1.0 - wd))
                    * (nk_vector[n] ** wd) for n in numbers}
        total = fsum(leaned_d.values())
        if total > 0:
            guarded = {n: v / total for n, v in leaned_d.items()}
            info["nkLeanApplied"] = True
    info["applied"] = True
    return guarded, info


def apply_override_guard(forecast: RaceForecast,
                         win_odds: Optional[dict] = None,
                         nk_forecast_odds: Optional[dict] = None):
    """Apply the override guard to a v9b RaceForecast.

    Returns (forecast, info); when the guard cannot fire (status
    not "ok", fewer than three scored runners, or an incomplete
    market) the SAME forecast object is returned with
    info["applied"] False and info["reason"] naming why. The
    rebuild is the exact construction postprocess_forecast uses:
    the guarded win probabilities ARE the effective PL strengths,
    so marginals, marks and tickets downstream stay consistent
    with them.
    """
    info = _info()
    if forecast.status != "ok":
        info["reason"] = forecast.status
        return forecast, info
    base = {}
    for r in forecast.runners:
        value = r.strength if r.strength is not None else r.p_win
        if value is None or value <= 0:
            continue
        base[r.number] = float(value)
    if len(base) < 3:
        info["reason"] = "insufficient-strengths"
        return forecast, info
    guarded, info = guard_probabilities(base, win_odds or {},
                                        nk_forecast_odds)
    if guarded is None:
        return forecast, info
    pl = marginals(distribution(dict(guarded)))
    ranked = sorted(pl, key=lambda n: (-pl[n][0], -pl[n][2], n))
    marks = _assign_marks(ranked, pl)
    runners = []
    for r in forecast.runners:
        if r.number in pl:
            runners.append(RunnerForecast(
                number=r.number, name=r.name,
                ability_score=r.ability_score,
                strength=round(guarded[r.number], 6),
                pace_adjustment=r.pace_adjustment,
                pace_reasons=r.pace_reasons,
                p_win=round(pl[r.number][0], 4),
                p_top2=round(pl[r.number][1], 4),
                p_top3=round(pl[r.number][2], 4),
                mark=marks.get(r.number, ""),
                status=r.status,
            ))
        else:
            runners.append(r)
    return RaceForecast(forecast.race_id, forecast.beta,
                        forecast.probability_status, tuple(runners),
                        "ok"), info
