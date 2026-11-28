"""Netkeiba-foundation forecast (2026-11-28 rebuild, stage 2;
the v3 corrections are the same day's follow-up measurement
and the v4 changes at the end of this docstring are the
same day's beat-the-market measurement).

Why this module exists — the user instruction of 2026-11-28:
"オリジナルださんでいい。とりあえずネット競馬を使って予想をしろ"
(issue the forecast from netkeiba's data; the in-house ability
stack no longer has to be the base). Stage 1 of the rebuild
(2026-11-28, clean-forecast-v1) had kept the v8/v9b ability
vector as the base and leaned two measured netkeiba signals
onto it. Stage 2 turns the construction around: the base
vector itself is built from netkeiba's published forecast
odds, corrected by the netkeiba signals that measured as
earning it ON THAT BASE, and blended once with the real
market. The ability stack (v8 elo/spd2 synthesis, the
temperature/blend post-processing) no longer touches the
issued probability on this path; the lane machinery still
runs to produce the runner skeleton, statuses and the
publishability decisions, and its vector is recorded in the
stage stamp as "preLean" for audit, but the issued vector is
the foundation's.

The measurement (saved official snapshots + the saved
netkeiba materials files, walk-forward: parameters read on
2026-11-23..25 tested on 11-26, re-read on 11-23..26 tested
on 11-27/28 NAR; 193 races with full market and forecast-odds
coverage, 79 of them in the two test folds):

  * market alone (multiplicative devig): combined test
    LogLoss 1.6695, top-pick 45.6%;
  * stage-1 v1 as measurable (issued vector + guard A-D on
    fold 1, the standing vector on fold 2): 1.6806 / 44.3% —
    strong on 11-26 (1.5573) and poor on 11-27 (1.8356),
    where the day's stack distortions were worst;
  * the nk base alone (power devig of the forecast odds,
    temperature 1.1): 1.5941 / 1.7429 on the two test folds —
    already at market level before any correction;
  * the adopted foundation (below): 1.5360 / 1.7031,
    combined 1.6100, top-pick 46.8% — better than both
    baselines on log loss in both folds (the same
    construction without the pace correction measures
    1.5182 / 1.6870; the pace paragraph below explains why
    the correction is in despite that difference);
  * the same foundation plus the override guard A-D was
    WORSE on log loss in all four learn/test comparisons at
    the adopted blend weight (combined 1.6110) and better
    only on top-pick rate by one race per fold (50.6%): the
    guard is therefore NOT part of this path (its step A
    would also replace the netkeiba vector with the market
    exactly when the two disagree, which contradicts the
    foundation's premise). The publisher's guard-upgrade
    machinery is disqualified for products stamped with
    this version, so the missing guard stamp can never
    deadlock a re-issue.

Per-signal walk-forward on the nk base (geometric lean,
weight selected on the learning fold only) — what earned a
place and what did not:

  * time index nk_best: -0.016 / -0.025 log loss on the two
    learning folds (fires on ~97% of races) — ADOPTED, w=0.20;
  * course jockey win rate (the horse's jockey's record at
    today's course, from the course-analysis persons table):
    -0.014 / -0.015 — ADOPTED, w=0.20 (fires only where the
    persons table covers >=60% of the field, ~1/3 of races);
  * CP forecast points (netkeiba's own computer-forecast
    newspaper column, point-scored): -0.008 / -0.007 —
    ADOPTED, w=0.10;
  * Maria pro index: +0.003 / -0.003 — NOT adopted: on the
    ability stack (stage 1) it carried information the stack
    lacked, but netkeiba's forecast odds already price it,
    so on this base it measures as zero. Same for the baba
    index (+0.004 / -0.005);
  * press aggregate, nk_avg5 / nk_recent5: small gains,
    crowded out by the adopted set (the greedy selection's
    marginal threshold) — not adopted;
  * best time, pedigree siblings, course / distance
    aptitude: zero to harmful on this base — not adopted;
  * the pace forecast (user instruction 2026-11-28: it
    MUST be used): nine forms were measured — start / C4
    positions raw, style categories both directions, the
    arrow (start->C4 predicted movement) raw, categorised
    and per-corner, and the pace-label interaction. Every
    "back the predicted shape" form measured harmful on
    this base, because the forecast odds already price
    netkeiba's own pace map. The one form with gains on
    both learning folds standalone (-0.019 / -0.009) is
    the arrow FADE (below): ADOPTED at w=0.10, first in
    the correction order. After the other corrections and
    the blend its marginal effect is slightly negative
    (test folds +0.018 / +0.016) — the other stages absorb
    most of the same over-reaction — and it is kept at
    the smallest grid weight on the user's instruction,
    with the cost recorded here rather than hidden;
  * AI-forecast marks, form deviation, horse-analysis
    grades, press rating, stretch: saved coverage too thin
    to measure on this corpus (the AI column's per-horse
    marks reach >=60% of a field in 0 of 193 races) — not
    adopted; still collected and displayed.

The path, in one line:

  stage 1  nk base     netkeiba forecast odds -> Shin
                       devig -> temperature 1.1
  stage 2  corrections z-leans, in order: pace arrow
                       fade 0.10, nk_best 0.20, course
                       jockey 0.20, CP points 0.10 (each
                       fires only at >=60% field coverage;
                       a runner without the signal takes
                       z=0, never an estimate)
  stage 3  market      ONE geometric blend with the real
           blend       market (Shin devig) at market
                       weight 0.45 (selected on the
                       learning folds; 0.30 and 0.60 both
                       measured worse out of sample)
  stage 4  popularity  a fixed log-bias per popularity
           calibration band (1st / 2-3 / 4-5 / 6+ by the
                       market win odds), fitted on the
                       saved corpus and shrunk x0.5 (the
                       v3 note below)
  stage 5  —           no guard, no further layers.

V3 changes (2026-11-28 follow-up; measured on the same
corpus and the same two walk-forward folds as everything
above — the correction-validation measurement):

  * devig: the base's power devig and the market's
    multiplicative devig are both replaced by Shin's
    method. No parameter is fitted — an arithmetic swap
    only. Combined test LogLoss 1.6100 -> 1.5859 (folds
    1.5133 / 1.6772), better in both folds, top-pick rate
    unchanged; most of the gain is on the market side
    (Shin alone also beat multiplicative for the market
    alone, 1.6460 vs 1.6695, the same direction as an
    earlier in-house measurement).
  * popularity-band calibration: on top of the Shin
    vectors the pipeline still under-prices the favourite
    and over-prices longshots (the favourite/longshot
    bias). Fitted per fold on the learning races only,
    the biases came out at +0.346 / +0.360 for the
    favourite and -0.296 / -0.145 for 6th-favourite-or-
    lower in the two folds — the same direction both
    times. With the fold-fitted biases the stack measures
    a combined 1.5771 (folds 1.5067 / 1.6655), the best
    of every configuration measured, at one race's cost
    in top-pick rate (45.6% vs 46.8%). The production
    constants (POPULARITY_BAND_BIASES) are fitted once on
    the full measured corpus (the 193 races with full
    forecast-odds and market coverage) on this v3
    pipeline, then SHRUNK by POPULARITY_BAND_SHRINK =
    0.5: the fitted magnitudes are large for a
    4-parameter fit, and the measurement report asked
    for the shrink as caution. The unshrunk fit is
    recorded next to the constants. The calibration runs
    only where the market blend ran (it needs the market
    odds to rank popularity); the market-base fallback
    below stays the raw market vector, exactly as the
    fallback contract has always promised.

V4 changes (2026-11-28 beat-the-market measurement; 179
configurations measured on the same corpus and folds, see
the measurement report): ONE configuration beat both the
market (Shin) and v3 on the test folds — combined 1.5395
vs market 1.6460 and v3 1.5755, better in both folds —
but the evidence is NAR ONLY: both test folds are entirely
NAR races, and on the small JRA auxiliary check (22 races
of 2026-11-23, within-day split) the winning configuration
measured WORSE than v3 and worse than the market. V4
therefore applies the winning configuration to the NAR
circuit only; the JRA circuit (jra_flat / debut / jumps)
keeps the v3 configuration byte-identical. The circuit is
resolved from the publisher's segment (or the race id
prefix) and recorded in the stamp. The three changes, NAR
only:

  * the pace-arrow fade lean is REPLACED by a pace
    scenario mixture: three scenarios (slow / average /
    high pace) with probabilities pi = softmax(-t, 0, +t),
    t = 2.6 * (L - 2.5) / 1.5, L = the number of runners
    whose predicted start percentile is <= 0.25. Each
    runner's probability is multiplied by
    pi_slow * exp(+1.5 f) + pi_avg + pi_high * exp(-1.5 f),
    f = 0.5 - start percentile (front-runners positive;
    a runner without a start percentile takes f = 0),
    then renormalised. The mixture fires only at >=60%
    field coverage of the start percentile, like a lean.
    On the (beta, w) grid the gain was monotone up to the
    adopted (2.6, 1.5), the plateau's most conservative
    point; the other three leans (nk_best 0.20, course
    jockey 0.20, CP points 0.10) are unchanged.
  * the base temperature is 1.25 instead of 1.1 (the
    temperature grid's best point on both folds);
  * the popularity-band calibration biases are fitted
    PER CIRCUIT. The production NAR constants
    (POPULARITY_BAND_BIASES_NAR) are the measurement's
    NAR fit on the fold-2 learning races (2026-11-23..26)
    over the v4 pipeline, shrunk by the same 0.5; the
    JRA circuit keeps the pooled v3 constants above.

V5 changes (2026-11-28, later the same day; the two
circuit-specific follow-up measurements — beat-market-nar2
for NAR, beat-market-jra for JRA — each measured on its own
circuit's saved corpus with the same walk-forward folds as
everything above). The circuits now differ in construction,
not only in constants, and each side's additions are the
parts that measured as earning it on THAT circuit:

  NAR (the v4 winning configuration plus three additions;
  validation 79 races: LogLoss 1.5395 -> 1.5279, top-pick
  46.8% -> 48.1%, better in both folds, stable across the
  neighbouring weights 1.5279..1.5301):
  * rotation bucket lean (w=0.10, after press_cp): the
    days since the runner's previous start, bucketed
    <=14 days -> +1, 15..35 -> 0, >=36 -> -1. The
    continuous -log(days) form failed on fold 2; only the
    bucket (short-interval runners lifted) survived. The
    signal is built from the runner's career history as
    the detail itself carries it (allPastRuns /
    recentRaces), runs dated before the race date only;
  * venue aptitude lean (w=0.10, after the rotation
    lean): the sign-flipped mean finish position at
    today's venue (finish / field size, averaged over
    the runner's past runs at the same track, pre-race
    runs only). The win-rate and top-3-rate forms of the
    same idea measured worse; the mean-finish form was
    the one that held in both folds;
  * the pace scenario mixture's strength w rises
    1.5 -> 2.0 (NAR only; alone it costs top-pick rate,
    with the two leans above it measures best).
  Caveat recorded by the measurement: the two leans'
  selection used the validation folds' results, so the
  -0.012 gain includes selection upside, and on the
  learning folds the additions score slightly WORSE than
  the v4 configuration — a provisional gain that forward
  data must confirm, adopted on the user's instruction
  to use what the validation numbers support.

  JRA (the v3 skeleton plus the combo5 additions;
  validation 67 races of the 89-race JRA corpus: LogLoss
  2.0963 (v3) -> 2.0662, market 2.1162, top-pick 23.9%
  -> 25.4% = the market's rate; better than both
  benchmarks combined and in folds A and C, worse in
  fold B — the day the market itself was strongest and
  every one of the 39 measured patterns lost to it):
  * press_all lean (w=0.30, after press_cp): the
    point-scored sum of ALL newspaper tipsters' marks
    (◎5 ○4 ▲3 △2 ☆1), not only the CP column. The CP
    column alone covers 14.6% of JRA runners and never
    passes the 60% gate there; the aggregate covers
    92.2% and was the largest single gain measured on
    the JRA corpus (alone: 2.0851, top-pick 28.4%);
  * pace-label scenario mixture (after the leans,
    before the blend): the same three-scenario mixture
    shape as NAR but the scenario tilt t comes from the
    race's pace label (paceLabel in the materials
    entry): H -> +2.6, S -> -2.6, anything else
    (including no label) -> 0, with w=1.5 on the start
    percentile. The NAR form (t from the front-runner
    COUNT) measured as a clear loss on JRA in every
    refit tried; the label form is a different mechanism
    and the two must not be conflated. A race whose
    label is absent still gets the symmetric (t=0)
    mixture when the start percentiles cover the field
    — that is the measured construction;
  * base temperature by field size: <=13 runners ->
    1.0, >=14 runners -> 1.25 (the same point selected
    on every fold; the field-size split of the
    CALIBRATION was also measured and was harmful, so
    the calibration stays the pooled v3 constants).
  The class-movement candidate was dropped unmeasured:
  neither the corpus nor the materials carry a class
  field. Course-aptitude and shrunk course-persons
  leans measured at or below v3 after press_all and
  are not in. An unresolved circuit (segment=None)
  keeps the v3 configuration exactly, as the
  conservative default.

Fallbacks (stamped, never silent): when the forecast odds
do not cover every runner of the vector, the base is the
real market's Shin-devig vector (base="market") and stages
2-4 do not run; when neither odds set covers the field, the
lane vector stands (base="lane", applied=False) — no number
is ever invented. Every stage's win vector is returned in
the info dict so the publisher can stamp it: the next
ablation reads saved vectors instead of reconstructing.

Determinism: the path is a pure function of (forecast
skeleton, materials entry, win odds) — no clocks, no
randomness, no network.
"""

from __future__ import annotations

from datetime import date as _date
from math import exp, fsum, sqrt

from ..safety.probability import distribution, marginals
from .forecast import RaceForecast, RunnerForecast, _assign_marks

CLEAN_FORECAST_VERSION = "clean-forecast-v5"

NK_TEMPERATURE = 1.1
# NAR circuit (v4): the beat-the-market measurement's
# temperature grid point — see the module docstring.
NK_TEMPERATURE_NAR = 1.25
# JRA circuit (v5): the base temperature depends on the
# field size — the beat-market-jra measurement's fs-tau
# point, selected identically on every fold (the pooled
# 1.1 sits between the two and was worse than the split
# on the learning folds).
NK_TEMPERATURE_JRA_SMALL_FIELD = 1.0
NK_TEMPERATURE_JRA_LARGE_FIELD = 1.25
JRA_FIELD_SIZE_BOUNDARY = 13
MARKET_BLEND_WEIGHT = 0.45
LEAN_MIN_COVERAGE = 0.60

# Popularity-band calibration (stage 4, v3). Bands by the
# market win-odds rank at issuance: favourite / 2nd-3rd /
# 4th-5th / 6th or lower. The biases are log-biases fitted
# by maximum likelihood on the full measured corpus (the
# 193 races with full forecast-odds and market coverage,
# 2026-11-23..28) over this module's own uncalibrated v3
# vectors, then shrunk by POPULARITY_BAND_SHRINK (the
# measurement's caution: the fitted magnitudes are large
# for a 4-parameter fit). Unshrunk fit on the corpus:
# (+0.3442, +0.0208, -0.1684, -0.1966) for the bands
# (1 / 2-3 / 4-5 / 6+); the constants below are that fit
# at shrink 0.5, rounded to 4 decimals.
POPULARITY_BANDS = ("1", "2-3", "4-5", "6+")
POPULARITY_BAND_SHRINK = 0.5
POPULARITY_BAND_BIASES = (0.1721, 0.0104, -0.0842, -0.0983)

# NAR circuit (v4): the popularity-band biases fitted on
# the NAR races only — the beat-the-market measurement's
# per-circuit fit (fold-2 learning races, 2026-11-23..26,
# over this module's v4 NAR pipeline), shrunk by the same
# POPULARITY_BAND_SHRINK = 0.5, rounded to 3 decimals as
# published in the measurement report. The JRA circuit
# keeps the pooled constants above (the per-circuit JRA
# fit rests on 22 races and measured unstably, and the
# winning configuration itself did not transfer to JRA).
POPULARITY_BAND_BIASES_NAR = (0.180, 0.009, -0.165, -0.024)

# Correction leans, in application order: (signal name,
# weight). The signal extractors are the *_signal functions
# below; the order is the greedy selection's order on the
# larger learning fold, with the pace-arrow correction
# first because it corrects the base's own construction
# (see the module docstring).
LEAN_SPECS = (("pace_arrow", 0.10), ("nk_best", 0.20),
              ("course_jockey", 0.20), ("press_cp", 0.10))

# NAR circuit (v4, v5): the pace-arrow fade is replaced by
# the pace scenario mixture below, so the NAR lean set is
# the other three corrections in the same relative order,
# plus (v5) the two history leans at the end — the
# rotation bucket and the venue aptitude, in the order
# the beat-market-nar2 measurement stacked them (both
# after press_cp, before the scenario mixture).
LEAN_SPECS_NAR = (("nk_best", 0.20), ("course_jockey", 0.20),
                  ("press_cp", 0.10), ("rotation_bucket", 0.10),
                  ("venue_avgfin", 0.10))

# JRA circuit (v5): the v3 lean set plus the press_all
# aggregate (the summed newspaper marks) after press_cp —
# the beat-market-jra measurement's largest single gain.
# The CP column stays in the set at its v3 weight (the
# measurement's skeleton kept it; on JRA fields it rarely
# passes the coverage gate, which the gate decides per
# race, exactly as measured).
LEAN_SPECS_JRA = (("pace_arrow", 0.10), ("nk_best", 0.20),
                  ("course_jockey", 0.20), ("press_cp", 0.10),
                  ("press_all", 0.30))

# Pace scenario mixture (NAR, v4): scenario probabilities
# pi = softmax(-t, 0, +t) over (slow, average, high) with
# t = SCENARIO_BETA * (L - SCENARIO_CENTER_LEADERS)
#     / SCENARIO_T_SCALE,
# L = number of covered runners whose predicted start
# percentile is <= SCENARIO_LEADER_MAX_PCT. A runner's
# multiplier is pi_slow * exp(+SCENARIO_W * f) + pi_avg
# + pi_high * exp(-SCENARIO_W * f) with f = 0.5 - start
# percentile. The (beta, w) point is the plateau's most
# conservative point of the measured grid.
SCENARIO_BETA = 2.6
SCENARIO_W = 1.5
SCENARIO_T_SCALE = 1.5
SCENARIO_CENTER_LEADERS = 2.5
SCENARIO_LEADER_MAX_PCT = 0.25

# NAR circuit (v5): the scenario mixture's strength rises
# to 2.0 — the beat-market-nar2 measurement's plateau
# point when combined with the two history leans (alone
# it cost top-pick rate; combined it measured best).
SCENARIO_W_NAR = 2.0

# Pace-LABEL scenario mixture (JRA, v5): the same mixture
# shape, but the tilt t is beta * (+1 for an H label,
# -1 for S, 0 otherwise) from the race's pace label —
# a different mechanism from the NAR count-based tilt
# above (which measured as a clear loss on JRA). The
# (beta, w) point was selected identically on every fold
# of the beat-market-jra measurement.
LABEL_SCENARIO_BETA = 2.6
LABEL_SCENARIO_W = 1.5

_PRESS_POINTS = {"◎": 5, "○": 4, "▲": 3, "△": 2, "☆": 1}


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _rebuild(forecast: RaceForecast, win_probs: dict) -> RaceForecast:
    """The exact rebuild construction postprocess_forecast and
    the override guard use: the new win probabilities ARE the
    effective PL strengths, marginals and marks are re-derived
    from them, so marks and tickets downstream stay consistent
    with the foundation vector."""
    pl = marginals(distribution(dict(win_probs)))
    ranked = sorted(pl, key=lambda n: (-pl[n][0], -pl[n][2], n))
    marks = _assign_marks(ranked, pl)
    runners = []
    for r in forecast.runners:
        if r.number in pl:
            runners.append(RunnerForecast(
                number=r.number, name=r.name,
                ability_score=r.ability_score,
                strength=round(win_probs[r.number], 6),
                pace_adjustment=r.pace_adjustment,
                pace_reasons=r.pace_reasons,
                p_win=round(pl[r.number][0], 4),
                p_top2=round(pl[r.number][1], 4),
                p_top3=round(pl[r.number][2], 4),
                mark=marks.get(r.number, ""),
                status=r.status))
        else:
            runners.append(r)
    return RaceForecast(forecast.race_id, forecast.beta,
                        forecast.probability_status, tuple(runners),
                        "ok")


def _win_vector(forecast: RaceForecast) -> dict:
    return {r.number: r.p_win for r in forecast.runners
            if r.p_win is not None and r.p_win > 0}


def power_devig(odds: dict, numbers) -> dict | None:
    """Power-method devig: implied probabilities raised to
    the exponent k that makes them sum to 1 (k solved by
    bisection). Returns None unless every number carries a
    usable odd (> 1.0). This was the v2 base's devig;
    v3 devigs with shin_devig instead (see the module
    docstring) and the function is retained only so the
    two stages' measurements stay reproducible."""
    raw = {}
    for n in numbers:
        value = _num(odds.get(n))
        if value is None or value <= 1.0:
            return None
        raw[n] = 1.0 / value
    lo, hi = 0.5, 2.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if fsum(v ** mid for v in raw.values()) > 1.0:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2.0
    out = {n: raw[n] ** k for n in numbers}
    total = fsum(out.values())
    return {n: out[n] / total for n in numbers}


def shin_devig(odds: dict, numbers) -> dict | None:
    """Shin's devig: the implied probabilities are read as
    a mix of informed and uninformed money, with the
    informed share z solved (bisection) so the corrected
    probabilities sum to 1. Returns None unless every
    number carries a usable odd (> 1.0). The arithmetic is
    the measured implementation verbatim — v3 replaced
    both the base's power devig and the market's
    multiplicative devig with this (module docstring)."""
    numbers = list(numbers)
    q = {}
    for n in numbers:
        value = _num(odds.get(n))
        if value is None or value <= 1.0:
            return None
        q[n] = 1.0 / value
    big_q = fsum(q.values())

    def total(z):
        return fsum(
            (sqrt(z * z + 4 * (1 - z) * q[n] ** 2 / big_q) - z)
            / (2 * (1 - z)) for n in numbers)

    lo, hi = 1e-9, 0.5
    if total(hi) > 1.0:
        z = hi
    else:
        for _ in range(80):
            mid = (lo + hi) / 2
            if total(mid) > 1.0:
                lo = mid
            else:
                hi = mid
        z = (lo + hi) / 2
    out = {n: (sqrt(z * z + 4 * (1 - z) * q[n] ** 2 / big_q) - z)
           / (2 * (1 - z)) for n in numbers}
    t = fsum(out.values())
    return {n: out[n] / t for n in numbers}


def popularity_band_map(win_odds: dict, numbers) -> dict | None:
    """{number: band index} by the market win-odds rank:
    rank 1 -> band 0, ranks 2-3 -> band 1, ranks 4-5 ->
    band 2, rank 6 or lower -> band 3. Equal odds break
    by horse number (the measured construction). None
    unless every number carries a usable odd (> 1.0)."""
    values = {}
    for n in numbers:
        value = _num(win_odds.get(n))
        if value is None or value <= 1.0:
            return None
        values[n] = value
    order = sorted(numbers, key=lambda n: (values[n], n))
    out = {}
    for i, n in enumerate(order):
        rank = i + 1
        out[n] = 0 if rank == 1 else 1 if rank <= 3 \
            else 2 if rank <= 5 else 3
    return out


def apply_band_calibration(vec: dict, bands: dict,
                           biases) -> dict:
    """Multiply each runner's probability by exp(bias of
    its popularity band) and renormalise — the measured
    stage-4 construction, verbatim."""
    out = {n: vec[n] * exp(biases[bands[n]]) for n in vec}
    total = fsum(out.values())
    return {n: v / total for n, v in out.items()}


def _temperature(vec: dict, tau: float) -> dict:
    if tau == 1.0:
        return dict(vec)
    out = {n: v ** tau for n, v in vec.items()}
    total = fsum(out.values())
    return {n: v / total for n, v in out.items()}


def z_lean(win_probs: dict, signal: dict, weight: float):
    """Geometric lean of a win vector toward a signal's
    within-race z-softmax distribution. Returns (vector,
    fired). Fires only at >= LEAN_MIN_COVERAGE field
    coverage; missing runners take z = 0. Pure and
    deterministic. (Same construction as stage 1, kept so
    the two stages' measurements stay comparable.)"""
    numbers = sorted(win_probs)
    covered = [n for n in numbers if _num(signal.get(n)) is not None]
    if not numbers or len(covered) < LEAN_MIN_COVERAGE * len(numbers):
        return dict(win_probs), False
    values = {n: _num(signal[n]) for n in covered}
    mean = fsum(values.values()) / len(values)
    var = fsum((v - mean) ** 2 for v in values.values()) / len(values)
    sd = sqrt(var)
    if sd <= 1e-9:
        return dict(win_probs), False
    raw = {}
    for n in numbers:
        z = (values[n] - mean) / sd if n in values else 0.0
        raw[n] = exp(z)
    total = fsum(raw.values())
    ref = {n: raw[n] / total for n in numbers}
    out = {n: win_probs[n] ** (1.0 - weight) * ref[n] ** weight
           for n in numbers}
    norm = fsum(out.values())
    return {n: out[n] / norm for n in numbers}, True


def _entry_horses(entry: dict | None) -> dict:
    if not isinstance(entry, dict):
        return {}
    horses = entry.get("horses")
    return horses if isinstance(horses, dict) else {}


def _horse(entry: dict | None, number: int) -> dict:
    horse = _entry_horses(entry).get(str(number))
    return horse if isinstance(horse, dict) else {}


def nk_forecast_odds(entry: dict | None) -> dict:
    """{horse number: netkeiba forecast win odd} from the
    materials entry (the per-horse odds.forecastWin the
    collection saved)."""
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        value = _num((horse.get("odds") or {}).get("forecastWin"))
        if value is not None:
            out[number] = value
    return out


def pace_arrow_signal(entry: dict | None) -> dict:
    """The pace forecast's arrow, in the direction the
    walk-forward supports: corner4 pct MINUS start pct —
    positive for a horse netkeiba's pace forecast predicts
    will LOSE ground through the race. The raw arrow
    (predicted gainers) measured harmful in every form
    tried (raw positions, categories, label interaction,
    both as a lone lean and as a late correction); the fade
    was the one pace form with gains on both learning folds
    standalone (-0.019 / -0.009 log loss): the forecast odds
    over-price the horses their own pace forecast sends
    forward, and this lean takes that premium back. Needs
    both percentiles; a horse missing either is absent."""
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        pace = horse.get("pace")
        if not isinstance(pace, dict):
            continue
        start = _num((pace.get("start") or {}).get("pct"))
        c4 = _num((pace.get("corner4") or {}).get("pct"))
        if start is not None and c4 is not None:
            out[number] = c4 - start
    return out


def pace_start_signal(entry: dict | None) -> dict:
    """{horse number: predicted start percentile} from the
    pace forecast — the scenario mixture's input (the same
    percentile the arrow fade reads as its start point). A
    horse without a start percentile is absent."""
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        pace = horse.get("pace")
        if not isinstance(pace, dict):
            continue
        start = _num((pace.get("start") or {}).get("pct"))
        if start is not None:
            out[number] = start
    return out


def _scenario_mixture(win_probs: dict, signal: dict,
                      t: float, w: float):
    """The shared three-scenario mixture arithmetic: pi =
    softmax(-t, 0, +t) over (slow, average, high); each
    runner is multiplied by pi_slow * exp(+w f) + pi_avg
    + pi_high * exp(-w f), f = 0.5 - start percentile
    (a runner without the signal takes f = 0), and the
    vector is renormalised. Returns (vector, pi)."""
    numbers = sorted(win_probs)
    e_slow, e_avg, e_high = exp(-t), 1.0, exp(t)
    pi_total = e_slow + e_avg + e_high
    pi = (e_slow / pi_total, e_avg / pi_total,
          e_high / pi_total)
    covered = {n for n in numbers
               if _num(signal.get(n)) is not None}
    out = {}
    for n in numbers:
        f = (0.5 - signal[n]) if n in covered else 0.0
        mix = pi[0] * exp(w * f) + pi[1] + pi[2] * exp(-w * f)
        out[n] = win_probs[n] * mix
    total = fsum(out.values())
    return {n: v / total for n, v in out.items()}, pi


def pace_scenario_mix(win_probs: dict, signal: dict,
                      beta: float = SCENARIO_BETA,
                      w: float = SCENARIO_W):
    """The pace scenario mixture (NAR, v4 — the measured
    replacement for the pace-arrow fade; the arithmetic is
    the beat-the-market measurement's verbatim). Three
    scenarios (slow / average / high pace) get probabilities
    pi = softmax(-t, 0, +t), t = beta * (L - 2.5) / 1.5,
    L = the number of covered runners whose start
    percentile is <= 0.25; each runner's probability is
    multiplied by pi_slow * exp(+w f) + pi_avg
    + pi_high * exp(-w f), f = 0.5 - start percentile
    (front-runners positive; a runner without the signal
    takes f = 0), and the vector is renormalised. Returns
    (vector, info); fires only at >= LEAN_MIN_COVERAGE
    field coverage, like a lean."""
    numbers = sorted(win_probs)
    covered = [n for n in numbers
               if _num(signal.get(n)) is not None]
    info = {"applied": False, "beta": beta, "w": w,
            "leaders": None, "coverage": len(covered),
            "pi": None}
    if not numbers or len(covered) < LEAN_MIN_COVERAGE * len(numbers):
        return dict(win_probs), info
    leaders = sum(1 for n in covered
                  if signal[n] <= SCENARIO_LEADER_MAX_PCT)
    t = beta * (leaders - SCENARIO_CENTER_LEADERS) / SCENARIO_T_SCALE
    out, pi = _scenario_mixture(win_probs, signal, t, w)
    info.update({"applied": True, "leaders": leaders,
                 "pi": [round(p, 6) for p in pi]})
    return out, info


def pace_label_scenario_mix(win_probs: dict, signal: dict,
                            label,
                            beta: float = LABEL_SCENARIO_BETA,
                            w: float = LABEL_SCENARIO_W):
    """The pace-LABEL scenario mixture (JRA, v5 — the
    beat-market-jra measurement's combo5 part, verbatim).
    The same three-scenario mixture as pace_scenario_mix,
    but the tilt comes from the race's pace label (the
    materials entry's paceLabel): t = beta * (+1) for an
    "H" label, beta * (-1) for "S", and 0 for anything
    else — including a missing label, which therefore
    still applies the symmetric mixture when the start
    percentiles cover the field (the measured
    construction; the label selects the tilt, not whether
    the stage runs). Returns (vector, info); fires only
    at >= LEAN_MIN_COVERAGE field coverage of the start
    percentile, like a lean."""
    numbers = sorted(win_probs)
    covered = [n for n in numbers
               if _num(signal.get(n)) is not None]
    info = {"applied": False, "beta": beta, "w": w,
            "label": label if isinstance(label, str) else None,
            "coverage": len(covered), "pi": None}
    if not numbers or len(covered) < LEAN_MIN_COVERAGE * len(numbers):
        return dict(win_probs), info
    t = beta * (1.0 if label == "H" else
                -1.0 if label == "S" else 0.0)
    out, pi = _scenario_mixture(win_probs, signal, t, w)
    info.update({"applied": True,
                 "pi": [round(p, 6) for p in pi]})
    return out, info


def nk_best_signal(entry: dict | None) -> dict:
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        value = _num(horse.get("nk_best"))
        if value is not None:
            out[number] = value
    return out


def course_jockey_signal(entry: dict | None) -> dict:
    """The horse's jockey's win rate at today's course, from
    the entry's coursePersons block (the course-analysis
    persons table the collection saved per horse)."""
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        persons = horse.get("coursePersons")
        if not isinstance(persons, dict):
            continue
        jockey = persons.get("jockey")
        if not isinstance(jockey, dict):
            continue
        value = _num(jockey.get("winRate"))
        if value is not None:
            out[number] = value
    return out


def press_cp_signal(entry: dict | None) -> dict:
    """Point score of netkeiba's own computer-forecast
    newspaper column (CP予想) per horse: ◎5 ○4 ▲3 △2 ☆1,
    any other mark (消/×/…) 0. A horse the column did not
    mark at all is absent (the lean's coverage gate decides
    whether the column speaks for this race at all)."""
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        press = horse.get("press")
        if not isinstance(press, dict):
            continue
        marks = press.get("marks")
        if not isinstance(marks, dict) or "CP予想" not in marks:
            continue
        out[number] = _PRESS_POINTS.get(marks["CP予想"], 0)
    return out


def press_all_signal(entry: dict | None) -> dict:
    """Point-scored sum of ALL newspaper tipsters' marks
    per horse (◎5 ○4 ▲3 △2 ☆1, any other mark 0) — the
    aggregate the beat-market-jra measurement calls
    press_all, construction verbatim: a horse whose press
    block is absent is absent from the signal; a horse
    with a press block but no marks scores 0 (present).
    The CP column alone (press_cp_signal) covers too few
    JRA runners to pass the coverage gate; the aggregate
    is the form that measured."""
    out = {}
    for key, horse in _entry_horses(entry).items():
        if not isinstance(horse, dict):
            continue
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        press = horse.get("press")
        if not isinstance(press, dict):
            continue
        marks = press.get("marks")
        if not isinstance(marks, dict):
            marks = {}
        out[number] = sum(_PRESS_POINTS.get(mark, 0)
                          for mark in marks.values())
    return out


def _history_horses(history: dict | None) -> dict:
    if not isinstance(history, dict):
        return {}
    horses = history.get("horses")
    return horses if isinstance(horses, dict) else {}


def _parse_day(value):
    if not isinstance(value, str):
        return None
    try:
        return _date.fromisoformat(value)
    except ValueError:
        return None


def _past_runs(runs, race_day: _date) -> list:
    """One runner's past runs as the measurement built
    them (beat-market-nar2 prep, verbatim): the runs the
    detail carries (allPastRuns then recentRaces, in the
    caller's order), keeping runs with a date and a
    finish, de-duplicated on (date, track, raceNumber,
    distance) with the first occurrence winning, filtered
    to dates strictly before the race date, sorted by
    date. Runs from the race day itself or later can
    never enter a signal — no leakage by construction."""
    seen = set()
    past = []
    for run in runs or []:
        if not isinstance(run, dict):
            continue
        if not run.get("date") or not run.get("finish"):
            continue
        key = (run["date"], run.get("track"),
               run.get("raceNumber"), run.get("distance"))
        if key in seen:
            continue
        seen.add(key)
        day = _parse_day(run["date"])
        if day is not None and day < race_day:
            past.append((day, run))
    past.sort(key=lambda item: item[0])
    return [run for _, run in past]


def rotation_bucket_signal(history: dict | None) -> dict:
    """Days since the runner's previous start, bucketed
    (the beat-market-nar2 measurement's surviving form):
    <=14 days -> +1.0, 15..35 days -> 0.0, >=36 days ->
    -1.0. A runner with no pre-race past run is absent
    (the lean's z=0), never an estimate. The history
    argument is {"date": race date, "venue": track name,
    "horses": {str(number): [run, ...]}} as the publisher
    assembles it from the detail."""
    out = {}
    race_day = _parse_day(
        history.get("date") if isinstance(history, dict)
        else None)
    if race_day is None:
        return out
    for key, runs in _history_horses(history).items():
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        past = _past_runs(runs, race_day)
        if not past:
            continue
        last_day = _parse_day(past[-1]["date"])
        if last_day is None:
            continue
        days = (race_day - last_day).days
        out[number] = 1.0 if days <= 14 else \
            0.0 if days <= 35 else -1.0
    return out


def venue_avgfin_signal(history: dict | None) -> dict:
    """Venue aptitude (the beat-market-nar2 measurement's
    surviving form): the sign-flipped mean finish
    position at today's venue — finish / field size (a
    missing field size counts as 12, as measured),
    averaged over the runner's pre-race runs at the same
    track (the track name the race id carries). A runner
    with no pre-race run at the venue is absent."""
    out = {}
    if not isinstance(history, dict):
        return out
    race_day = _parse_day(history.get("date"))
    venue = history.get("venue")
    if race_day is None or not isinstance(venue, str) \
            or not venue:
        return out
    for key, runs in _history_horses(history).items():
        try:
            number = int(key)
        except (TypeError, ValueError):
            continue
        past = _past_runs(runs, race_day)
        local = [run for run in past
                 if run.get("track") == venue]
        if not local:
            continue
        values = []
        for run in local:
            finish = _num(run.get("finish"))
            if finish is None:
                continue
            values.append(finish / (run.get("fieldSize")
                                    or 12))
        if values:
            out[number] = -fsum(values) / len(values)
    return out


_SIGNAL_EXTRACTORS = {"pace_arrow": pace_arrow_signal,
                      "nk_best": nk_best_signal,
                      "course_jockey": course_jockey_signal,
                      "press_cp": press_cp_signal,
                      "press_all": press_all_signal}

# The leans whose signal is built from the runner's
# career history (the publisher's history argument)
# rather than from the materials entry.
_HISTORY_SIGNAL_EXTRACTORS = {
    "rotation_bucket": rotation_bucket_signal,
    "venue_avgfin": venue_avgfin_signal}


_CIRCUIT_BY_SEGMENT = {"nar": "nar", "jra": "jra",
                       "jra_flat": "jra", "debut": "jra",
                       "jumps": "jra"}


def _circuit_of(segment, race_id) -> str | None:
    """Resolve the circuit ("jra" / "nar") for the stamp
    and the v4 configuration split. The publisher's segment
    wins when given (its Segment values map jra_flat /
    debut / jumps onto the JRA circuit); otherwise the
    race id prefix decides. An unresolvable circuit returns
    None, which runs the pooled v3 configuration — the
    conservative default."""
    if segment is not None:
        return _CIRCUIT_BY_SEGMENT.get(segment)
    rid = race_id or ""
    if rid.startswith("nar"):
        return "nar"
    if rid.startswith("jra"):
        return "jra"
    return None


def _resolved_biases(circuit, band_biases):
    """(biases, fit) for a call: an explicit band_biases
    override wins (the walk-forward measurements pass
    their fold-fitted values); otherwise the NAR circuit
    takes its per-circuit constants and every other
    circuit the pooled v3 constants."""
    if band_biases is not None:
        return band_biases, "override"
    if circuit == "nar":
        return POPULARITY_BAND_BIASES_NAR, "nar-fit"
    return POPULARITY_BAND_BIASES, "pooled-fit"


def nk_foundation_vector(numbers, entry: dict | None,
                         win_odds: dict,
                         band_biases=None,
                         segment: str | None = None,
                         history: dict | None = None):
    """The foundation's stages 1-4 on a plain win vector.
    Returns (vector, info); vector is None when neither the
    forecast odds nor the market covers the field (the
    caller then keeps the lane vector). info carries the
    stage vectors and the per-stage facts for the stamp.

    segment is the resolved circuit ("jra" / "nar" /
    None): "nar" runs the v5 NAR configuration (v4's
    winner — temperature 1.25, the count-based pace
    scenario mixture, per-circuit calibration biases —
    plus the rotation-bucket and venue-aptitude history
    leans and the mixture strength 2.0); "jra" runs the
    v5 JRA configuration (combo5: the v3 skeleton plus
    the press_all aggregate lean, the pace-LABEL scenario
    mixture, and the base temperature split by field
    size, with the pooled calibration biases); every
    other value runs the v3 configuration exactly.
    band_biases overrides the stage-4 calibration biases
    (the walk-forward measurements pass their fold-fitted
    values; production callers take the module constants
    for the circuit). history is the publisher's career-
    history argument ({"date", "venue", "horses"}) the
    NAR history leans read; without it those leans simply
    do not fire."""
    circuit = segment if segment in ("jra", "nar") else None
    nar = circuit == "nar"
    jra = circuit == "jra"
    numbers = sorted(numbers)
    if nar:
        tau = NK_TEMPERATURE_NAR
        lean_specs = LEAN_SPECS_NAR
    elif jra:
        tau = NK_TEMPERATURE_JRA_SMALL_FIELD \
            if len(numbers) <= JRA_FIELD_SIZE_BOUNDARY \
            else NK_TEMPERATURE_JRA_LARGE_FIELD
        lean_specs = LEAN_SPECS_JRA
    else:
        tau = NK_TEMPERATURE
        lean_specs = LEAN_SPECS
    band_biases, bias_fit = _resolved_biases(circuit,
                                             band_biases)
    info = {"base": None, "segment": circuit,
            "temperature": tau,
            "devig": "shin",
            "leans": {}, "coverage": {},
            "scenarioMix": {"applied": False,
                            "beta": SCENARIO_BETA,
                            "w": SCENARIO_W_NAR if nar
                            else SCENARIO_W,
                            "leaders": None, "coverage": 0,
                            "pi": None},
            "labelScenarioMix": {"applied": False,
                                 "beta": LABEL_SCENARIO_BETA,
                                 "w": LABEL_SCENARIO_W,
                                 "label": None, "coverage": 0,
                                 "pi": None},
            "blendApplied": False,
            "blendWeight": MARKET_BLEND_WEIGHT,
            "calibration": {"applied": False,
                            "bands": list(POPULARITY_BANDS),
                            "biases": [float(b)
                                       for b in band_biases],
                            "shrink": POPULARITY_BAND_SHRINK,
                            "segment": circuit,
                            "fit": bias_fit},
            "stages": {}}
    if not numbers:
        info["base"] = "lane"
        return None, info
    nk_odds = nk_forecast_odds(entry)
    info["coverage"]["nkForecast"] = sum(
        1 for n in numbers if n in nk_odds)
    base = shin_devig(nk_odds, numbers)
    if base is None:
        market = shin_devig(win_odds or {}, numbers)
        if market is None:
            info["base"] = "lane"
            return None, info
        info["base"] = "market"
        info["stages"]["nkBase"] = dict(market)
        info["stages"]["final"] = dict(market)
        return market, info
    info["base"] = "nk"
    current = _temperature(base, tau)
    info["stages"]["nkBase"] = dict(current)
    for name, weight in lean_specs:
        if name in _HISTORY_SIGNAL_EXTRACTORS:
            signal = _HISTORY_SIGNAL_EXTRACTORS[name](history)
        else:
            signal = _SIGNAL_EXTRACTORS[name](entry)
        covered = sum(1 for n in numbers if n in signal)
        info["coverage"][name] = covered
        current, fired = z_lean(current, signal, weight)
        info["leans"][name] = {"weight": weight, "fired": fired}
    info["stages"]["corrected"] = dict(current)
    if nar:
        start_signal = pace_start_signal(entry)
        info["coverage"]["pace_start"] = sum(
            1 for n in numbers if n in start_signal)
        current, mix_info = pace_scenario_mix(
            current, start_signal, w=SCENARIO_W_NAR)
        info["scenarioMix"] = mix_info
        info["stages"]["scenario"] = dict(current)
    elif jra:
        start_signal = pace_start_signal(entry)
        info["coverage"]["pace_start"] = sum(
            1 for n in numbers if n in start_signal)
        label = entry.get("paceLabel") \
            if isinstance(entry, dict) else None
        current, lab_info = pace_label_scenario_mix(
            current, start_signal, label)
        info["labelScenarioMix"] = lab_info
        info["stages"]["scenario"] = dict(current)
    if win_odds and all(_num(win_odds.get(n)) is not None
                         and _num(win_odds.get(n)) > 1.0
                         for n in numbers):
        market = shin_devig(win_odds, numbers)
        w = MARKET_BLEND_WEIGHT
        blended = {n: current[n] ** (1.0 - w) * market[n] ** w
                   for n in numbers}
        total = fsum(blended.values())
        current = {n: v / total for n, v in blended.items()}
        info["blendApplied"] = True
    info["stages"]["blended"] = dict(current)
    if info["blendApplied"]:
        bands = popularity_band_map(win_odds, numbers)
        if bands is not None:
            current = apply_band_calibration(current, bands,
                                             band_biases)
            info["calibration"]["applied"] = True
    info["stages"]["calibrated"] = dict(current)
    info["stages"]["final"] = dict(current)
    return current, info


def apply_nk_foundation(forecast: RaceForecast,
                        entry: dict | None,
                        win_odds: dict | None,
                        band_biases=None,
                        segment: str | None = None,
                        history: dict | None = None):
    """The whole netkeiba-foundation path for one race, over
    the caller's lane forecast (whose runners, names and
    statuses the rebuilt forecast keeps; its probabilities
    are replaced whenever the foundation can build a vector).
    Returns (forecast, info); info['pathApplied'] tells the
    publisher the issued vector is the foundation's (so the
    retired guard stage must not run on it), info['stages']
    carries every stage's win vector for the stamp,
    info['segment'] records the resolved circuit ("jra" /
    "nar" / None — from the segment argument when given,
    else the race id prefix), info['scenarioMix'] the NAR
    count-based pace scenario mixture's facts,
    info['labelScenarioMix'] the JRA pace-label scenario
    mixture's facts (the label included), info['leans'] /
    info['coverage'] every correction's weight, firing and
    coverage — the NAR history leans (rotation_bucket /
    venue_avgfin) included, so the stamp shows whether
    they spoke — and info['calibration'] the stage-4
    popularity-band calibration (bands, the biases used,
    the shrink, and the biases' provenance in 'fit').
    history is the publisher's career-history argument
    ({"date", "venue", "horses"}) for the NAR history
    leans; it is ignored on the other circuits."""
    circuit = _circuit_of(segment, forecast.race_id)
    resolved_biases, bias_fit = _resolved_biases(circuit,
                                                 band_biases)
    info = {"applied": False, "pathApplied": False,
            "version": CLEAN_FORECAST_VERSION, "base": None,
            "segment": circuit,
            "devig": "shin",
            "leans": {}, "coverage": {},
            "scenarioMix": {"applied": False,
                            "beta": SCENARIO_BETA,
                            "w": SCENARIO_W_NAR
                            if circuit == "nar"
                            else SCENARIO_W,
                            "leaders": None, "coverage": 0,
                            "pi": None},
            "labelScenarioMix": {"applied": False,
                                 "beta": LABEL_SCENARIO_BETA,
                                 "w": LABEL_SCENARIO_W,
                                 "label": None, "coverage": 0,
                                 "pi": None},
            "calibration": {"applied": False,
                            "bands": list(POPULARITY_BANDS),
                            "biases": [float(b) for b in
                                      resolved_biases],
                            "shrink": POPULARITY_BAND_SHRINK,
                            "segment": circuit,
                            "fit": bias_fit},
            "stages": {}}
    win = _win_vector(forecast)
    if not win:
        info["base"] = "lane"
        return forecast, info
    vector, finfo = nk_foundation_vector(
        sorted(win), entry, win_odds or {}, band_biases,
        segment=circuit, history=history)
    info.update({k: finfo[k] for k in
                 ("base", "segment", "temperature", "devig",
                  "leans", "coverage", "scenarioMix",
                  "labelScenarioMix",
                  "blendApplied", "blendWeight",
                  "calibration", "stages")})
    if vector is None:
        return forecast, info
    info["pathApplied"] = True
    info["applied"] = True
    return _rebuild(forecast, vector), info
