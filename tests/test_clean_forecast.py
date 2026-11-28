"""Netkeiba-foundation path (2026-11-28 rebuild stage 2):
the v2 probability path's contract tests.

Covered:
  * determinism — same inputs, byte-identical probabilities;
  * the base is netkeiba's — when the forecast odds rank a
    different horse first than the lane vector does, the
    foundation follows the forecast odds, not the lane;
  * marks consistency — the marks on the final forecast are
    exactly the probability ranking's marks (◎○▲△ by win
    probability, ☆ the best top-3 probability of the rest);
  * tickets derive from the same ranking and name only
    runners of the final forecast;
  * lean gates — a correction fires only at >=60% field
    coverage, and a runner without the signal is never
    given an estimated value;
  * the pace arrow runs in the measured (fade) direction;
  * Maria is not an input on this path (it measured as
    zero on the netkeiba base — the forecast odds already
    price it);
  * fallbacks — incomplete forecast odds fall back to the
    market base; no usable odds at all keeps the lane
    vector untouched;
  * stage composition — base, corrections and blend run in
    order, every stage vector is recorded, and there is no
    post-blend stage (the retired guard is not in the path).
"""

from rewrite.analysis.clean_forecast import (
    CLEAN_FORECAST_VERSION, apply_nk_foundation, power_devig,
    z_lean)
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.tickets import generate_tickets

ODDS = {1: 2.0, 2: 3.5, 3: 5.0, 4: 8.0, 5: 12.0, 6: 20.0,
        7: 30.0, 8: 50.0}
STRENGTHS = {1: 0.30, 2: 0.22, 3: 0.16, 4: 0.11, 5: 0.08,
             6: 0.06, 7: 0.04, 8: 0.03}
NK_ODDS = {1: 2.4, 2: 3.2, 3: 4.6, 4: 7.5, 5: 13.0, 6: 18.0,
           7: 34.0, 8: 44.0}


def _forecast():
    runners = tuple(
        RunnerForecast(
            number=n, name=f"horse-{n}", ability_score=50.0,
            strength=STRENGTHS[n], pace_adjustment=1.0,
            pace_reasons=(), p_win=STRENGTHS[n], p_top2=None,
            p_top3=None, mark="", status="ok")
        for n in sorted(STRENGTHS))
    return RaceForecast("test-race", 3.0, "uncalibrated",
                        runners, "ok")


def _entry(nk_odds=None, nk_best=None, pace=None, jockey=None,
           cp=None, maria=None):
    horses = {}
    for n in sorted(STRENGTHS):
        row = {}
        if nk_odds and n in nk_odds:
            row["odds"] = {"forecastWin": nk_odds[n]}
        if nk_best and n in nk_best:
            row["nk_best"] = nk_best[n]
        if pace and n in pace:
            start, c4 = pace[n]
            row["pace"] = {"start": {"pct": start},
                           "corner3": {"pct": (start + c4) / 2},
                           "corner4": {"pct": c4}}
        if jockey and n in jockey:
            row["coursePersons"] = {
                "jockey": {"winRate": jockey[n]}}
        if cp and n in cp:
            row["press"] = {"marks": {"CP予想": cp[n]}}
        if maria and n in maria:
            row["mariaIndex"] = maria[n]
        horses[str(n)] = row
    return {"horses": horses, "netkeibaRaceId": "20261128060101"}


def _full_entry(**kw):
    base = dict(
        nk_odds=NK_ODDS,
        nk_best={n: 90 - n for n in STRENGTHS},
        pace={n: (n / 10.0, (9 - n) / 10.0) for n in STRENGTHS},
        jockey={n: 0.05 + 0.01 * n for n in STRENGTHS},
        cp={n: "○" if n % 2 else "▲" for n in STRENGTHS})
    base.update(kw)
    return _entry(**base)


def _win(forecast):
    return {r.number: r.p_win for r in forecast.runners}


def test_determinism():
    entry = _full_entry()
    first, info1 = apply_nk_foundation(_forecast(), entry, ODDS)
    second, info2 = apply_nk_foundation(_forecast(), entry, ODDS)
    assert _win(first) == _win(second)
    assert info1["stages"] == info2["stages"]
    assert info1["version"] == CLEAN_FORECAST_VERSION == \
        "clean-forecast-v2"


def test_base_is_netkeiba_not_the_lane():
    # The lane vector ranks horse 1 first; the forecast odds
    # rank horse 8 first by a wide margin. The foundation's
    # top pick must follow the forecast odds.
    flipped = {1: 60.0, 2: 50.0, 3: 40.0, 4: 30.0, 5: 20.0,
               6: 12.0, 7: 6.0, 8: 2.2}
    final, info = apply_nk_foundation(
        _forecast(), _entry(nk_odds=flipped), ODDS)
    assert info["base"] == "nk" and info["pathApplied"]
    top = max(_win(final).items(), key=lambda kv: kv[1])[0]
    assert top == 8


def test_marks_follow_final_probabilities():
    final, _ = apply_nk_foundation(_forecast(), _full_entry(),
                                   ODDS)
    by_win = sorted(final.runners,
                    key=lambda r: (-r.p_win, -r.p_top3, r.number))
    expected = {}
    for i, symbol in enumerate(("◎", "○", "▲", "△")):
        expected[by_win[i].number] = symbol
    rest = by_win[4:]
    star = max(rest, key=lambda r: (r.p_top3, r.p_win, -r.number))
    expected[star.number] = "☆"
    actual = {r.number: r.mark for r in final.runners if r.mark}
    assert actual == expected


def test_tickets_derive_from_the_same_ranking():
    final, _ = apply_nk_foundation(_forecast(), _full_entry(),
                                   ODDS)
    plan = generate_tickets(final, ODDS, calibration_validated=False)
    marked = {r.number for r in final.runners if r.mark}
    assert len(marked) == 5
    tickets = plan.ev_tickets + plan.probability_tickets
    assert tickets
    for ticket in tickets:
        for number in ticket.selection:
            assert number in _win(final)


def test_lean_coverage_gate():
    base = {n: 1.0 / 8 for n in STRENGTHS}
    # 4 of 8 covered (50%) -> no fire
    out, fired = z_lean(base, {1: 90, 2: 80, 3: 70, 4: 60}, 0.2)
    assert not fired and out == base
    # 5 of 8 covered (62.5%) -> fires
    out, fired = z_lean(base, {1: 90, 2: 80, 3: 70, 4: 60, 5: 50},
                        0.2)
    assert fired and out != base
    # flat signal -> no fire (no information)
    out, fired = z_lean(base, {n: 70 for n in STRENGTHS}, 0.2)
    assert not fired


def test_foundation_lean_gate_and_missing_runner():
    # nk_best for only 3 of 8 horses: that lean must not
    # fire; the pace lean (full coverage) still does.
    entry = _full_entry(nk_best={1: 95, 2: 90, 3: 85})
    _, info = apply_nk_foundation(_forecast(), entry, ODDS)
    assert info["leans"]["nk_best"]["fired"] is False
    assert info["leans"]["pace_arrow"]["fired"] is True
    assert info["coverage"]["nk_best"] == 3


def test_pace_arrow_fades_predicted_gainers():
    # Horse 1 is the pace forecast's big predicted gainer
    # (start pct .95 -> corner4 pct .10); everyone else is
    # predicted to hold position. With everything else in
    # the two entries identical, horse 1's final probability
    # must be LOWER with the pace block than without it.
    gaining = {n: (0.5, 0.5) for n in STRENGTHS}
    gaining[1] = (0.95, 0.10)
    with_pace, _ = apply_nk_foundation(
        _forecast(), _full_entry(pace=gaining), ODDS)
    without, _ = apply_nk_foundation(
        _forecast(), _full_entry(pace=None), ODDS)
    assert _win(with_pace)[1] < _win(without)[1]


def test_maria_is_not_an_input():
    plain, _ = apply_nk_foundation(_forecast(), _full_entry(),
                                   ODDS)
    with_maria, _ = apply_nk_foundation(
        _forecast(),
        _full_entry(maria={n: 10 * n for n in STRENGTHS}), ODDS)
    assert _win(plain) == _win(with_maria)


def test_market_fallback_base():
    # No forecast odds in the entry: the base is the real
    # market's power-devig vector, verbatim (no corrections,
    # no blend on top of the market itself).
    final, info = apply_nk_foundation(
        _forecast(), _entry(), ODDS)
    assert info["base"] == "market" and info["pathApplied"]
    expected = power_devig(ODDS, sorted(STRENGTHS))
    got = _win(final)
    for n in STRENGTHS:
        assert abs(got[n] - round(expected[n], 4)) < 2e-4


def test_no_usable_odds_keeps_lane_vector():
    lane = _forecast()
    final, info = apply_nk_foundation(lane, None, {1: 2.0})
    assert info["base"] == "lane" and not info["pathApplied"]
    assert _win(final) == _win(lane)


def test_stages_recorded_in_order():
    final, info = apply_nk_foundation(_forecast(), _full_entry(),
                                      ODDS)
    stages = info["stages"]
    assert set(stages) == {"nkBase", "corrected", "blended",
                           "final"}
    assert info["blendApplied"] is True
    assert all(lean["fired"] for lean in info["leans"].values())
    # No post-blend stage exists on this path: the recorded
    # final vector IS the blended vector, and it is the
    # vector the rebuilt forecast carries (rounded).
    assert stages["final"] == stages["blended"]
    for n, p in stages["final"].items():
        assert abs(_win(final)[n] - round(p, 4)) < 2e-4
