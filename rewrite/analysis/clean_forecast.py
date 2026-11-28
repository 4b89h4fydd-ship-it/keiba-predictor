"""Netkeiba-foundation forecast (2026-11-28 rebuild, stage 2).

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

  stage 1  nk base     netkeiba forecast odds -> power
                       devig -> temperature 1.1
  stage 2  corrections z-leans, in order: pace arrow
                       fade 0.10, nk_best 0.20, course
                       jockey 0.20, CP points 0.10 (each
                       fires only at >=60% field coverage;
                       a runner without the signal takes
                       z=0, never an estimate)
  stage 3  market      ONE geometric blend with the real
           blend       market (multiplicative devig) at
                       market weight 0.45 (selected on the
                       learning folds; 0.30 and 0.60 both
                       measured worse out of sample)
  stage 4  —           no guard, no further layers.

Fallbacks (stamped, never silent): when the forecast odds
do not cover every runner of the vector, the base is the
real market's power-devig vector (base="market") and stages
2-3 do not run; when neither odds set covers the field, the
lane vector stands (base="lane", applied=False) — no number
is ever invented. Every stage's win vector is returned in
the info dict so the publisher can stamp it: the next
ablation reads saved vectors instead of reconstructing.

Determinism: the path is a pure function of (forecast
skeleton, materials entry, win odds) — no clocks, no
randomness, no network.
"""

from __future__ import annotations

from math import exp, fsum, sqrt

from ..safety.probability import distribution, marginals
from .forecast import RaceForecast, RunnerForecast, _assign_marks
from .shadow_v9 import market_probs

CLEAN_FORECAST_VERSION = "clean-forecast-v2"

NK_TEMPERATURE = 1.1
MARKET_BLEND_WEIGHT = 0.45
LEAN_MIN_COVERAGE = 0.60

# Correction leans, in application order: (signal name,
# weight). The signal extractors are the *_signal functions
# below; the order is the greedy selection's order on the
# larger learning fold, with the pace-arrow correction
# first because it corrects the base's own construction
# (see the module docstring).
LEAN_SPECS = (("pace_arrow", 0.10), ("nk_best", 0.20),
              ("course_jockey", 0.20), ("press_cp", 0.10))

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
    usable odd (> 1.0). Measured as the best of
    multiplicative / power / Shin for the netkeiba forecast
    odds on both learning folds."""
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


_SIGNAL_EXTRACTORS = {"pace_arrow": pace_arrow_signal,
                      "nk_best": nk_best_signal,
                      "course_jockey": course_jockey_signal,
                      "press_cp": press_cp_signal}


def nk_foundation_vector(numbers, entry: dict | None,
                         win_odds: dict):
    """The foundation's stages 1-3 on a plain win vector.
    Returns (vector, info); vector is None when neither the
    forecast odds nor the market covers the field (the
    caller then keeps the lane vector). info carries the
    stage vectors and the per-stage facts for the stamp."""
    info = {"base": None, "temperature": NK_TEMPERATURE,
            "leans": {}, "coverage": {},
            "blendApplied": False,
            "blendWeight": MARKET_BLEND_WEIGHT,
            "stages": {}}
    numbers = sorted(numbers)
    if not numbers:
        info["base"] = "lane"
        return None, info
    nk_odds = nk_forecast_odds(entry)
    info["coverage"]["nkForecast"] = sum(
        1 for n in numbers if n in nk_odds)
    base = power_devig(nk_odds, numbers)
    if base is None:
        market = power_devig(win_odds or {}, numbers)
        if market is None:
            info["base"] = "lane"
            return None, info
        info["base"] = "market"
        info["stages"]["nkBase"] = dict(market)
        info["stages"]["final"] = dict(market)
        return market, info
    info["base"] = "nk"
    current = _temperature(base, NK_TEMPERATURE)
    info["stages"]["nkBase"] = dict(current)
    for name, weight in LEAN_SPECS:
        signal = _SIGNAL_EXTRACTORS[name](entry)
        covered = sum(1 for n in numbers if n in signal)
        info["coverage"][name] = covered
        current, fired = z_lean(current, signal, weight)
        info["leans"][name] = {"weight": weight, "fired": fired}
    info["stages"]["corrected"] = dict(current)
    if win_odds and all(_num(win_odds.get(n)) is not None
                         and _num(win_odds.get(n)) > 1.0
                         for n in numbers):
        market = market_probs(win_odds, numbers)
        w = MARKET_BLEND_WEIGHT
        blended = {n: current[n] ** (1.0 - w) * market[n] ** w
                   for n in numbers}
        total = fsum(blended.values())
        current = {n: v / total for n, v in blended.items()}
        info["blendApplied"] = True
    info["stages"]["blended"] = dict(current)
    info["stages"]["final"] = dict(current)
    return current, info


def apply_nk_foundation(forecast: RaceForecast,
                        entry: dict | None,
                        win_odds: dict | None):
    """The whole netkeiba-foundation path for one race, over
    the caller's lane forecast (whose runners, names and
    statuses the rebuilt forecast keeps; its probabilities
    are replaced whenever the foundation can build a vector).
    Returns (forecast, info); info['pathApplied'] tells the
    publisher the issued vector is the foundation's (so the
    retired guard stage must not run on it), info['stages']
    carries every stage's win vector for the stamp."""
    info = {"applied": False, "pathApplied": False,
            "version": CLEAN_FORECAST_VERSION, "base": None,
            "leans": {}, "coverage": {}, "stages": {}}
    win = _win_vector(forecast)
    if not win:
        info["base"] = "lane"
        return forecast, info
    vector, finfo = nk_foundation_vector(
        sorted(win), entry, win_odds or {})
    info.update({k: finfo[k] for k in
                 ("base", "temperature", "leans", "coverage",
                  "blendApplied", "blendWeight", "stages")})
    if vector is None:
        return forecast, info
    info["pathApplied"] = True
    info["applied"] = True
    return _rebuild(forecast, vector), info
