"""Netkeiba-foundation path (2026-11-28 rebuild stage 2,
v3 corrections, v4 circuit split, v5 circuit-specific
configurations): the probability path's contract tests.

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
    market base (Shin devig, verbatim, no calibration);
    no usable odds at all keeps the lane vector untouched;
  * stage composition — base, corrections, blend and the
    popularity-band calibration run in order, every stage
    vector is recorded, and the calibration is the only
    post-blend stage (the retired guard is not in the
    path);
  * the calibration runs in the measured direction — it
    raises the market favourite's probability and lowers
    a 6th-favourite-or-lower runner's, relative to the
    blended vector;
  * v4 circuit split — the JRA circuit keeps the v3
    configuration exactly (temperature 1.1, the arrow
    fade, the pooled calibration biases, no scenario
    stage); the NAR circuit runs the measured winning
    configuration (temperature 1.25, the pace scenario
    mixture instead of the arrow fade, the per-circuit
    NAR calibration biases), the mixture fires only at
    >=60% start-percentile coverage, and it moves a
    front-runner's probability up when the field has few
    front-runners (slow scenario likely) and down when
    it has many (high scenario likely);
  * v5 circuit configurations — an unresolved circuit
    keeps the v3 configuration exactly. The NAR circuit
    adds the two history leans (rotation bucket, venue
    aptitude; both read only runs dated before the race
    date) after press_cp and strengthens the scenario
    mixture to w=2.0. The JRA circuit runs combo5: the
    press_all aggregate lean (all tipsters' marks summed,
    firing where the CP column alone cannot pass the
    gate), the pace-LABEL scenario mixture (H tilts to
    the high scenario, S to the slow, no label is the
    symmetric mixture), and the base temperature split
    by field size (<=13 runners 1.0, >=14 runners 1.25),
    with the pooled calibration biases unchanged.
"""

from rewrite.analysis.clean_forecast import (
    CLEAN_FORECAST_VERSION, POPULARITY_BAND_BIASES,
    POPULARITY_BAND_BIASES_NAR, apply_nk_foundation,
    press_all_signal, rotation_bucket_signal, shin_devig,
    venue_avgfin_signal, z_lean)
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.tickets import generate_tickets

ODDS = {1: 2.0, 2: 3.5, 3: 5.0, 4: 8.0, 5: 12.0, 6: 20.0,
        7: 30.0, 8: 50.0}
STRENGTHS = {1: 0.30, 2: 0.22, 3: 0.16, 4: 0.11, 5: 0.08,
             6: 0.06, 7: 0.04, 8: 0.03}
NK_ODDS = {1: 2.4, 2: 3.2, 3: 4.6, 4: 7.5, 5: 13.0, 6: 18.0,
           7: 34.0, 8: 44.0}


def _forecast(race_id="test-race"):
    runners = tuple(
        RunnerForecast(
            number=n, name=f"horse-{n}", ability_score=50.0,
            strength=STRENGTHS[n], pace_adjustment=1.0,
            pace_reasons=(), p_win=STRENGTHS[n], p_top2=None,
            p_top3=None, mark="", status="ok")
        for n in sorted(STRENGTHS))
    return RaceForecast(race_id, 3.0, "uncalibrated",
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
        "clean-forecast-v5"


def test_base_is_netkeiba_not_the_lane():
    # The lane vector ranks horse 1 first; the forecast odds
    # rank horse 8 first by a wide margin. The foundation
    # through the blend must follow the forecast odds. (The
    # stage-4 calibration may then tip a near-tie toward
    # the market favourite — here it does, 0.146 vs 0.154
    # blended — which is its measured purpose, so the
    # contract is asserted on the blended vector.)
    flipped = {1: 60.0, 2: 50.0, 3: 40.0, 4: 30.0, 5: 20.0,
               6: 12.0, 7: 6.0, 8: 2.2}
    final, info = apply_nk_foundation(
        _forecast(), _entry(nk_odds=flipped), ODDS)
    assert info["base"] == "nk" and info["pathApplied"]
    blended = info["stages"]["blended"]
    top = max(blended.items(), key=lambda kv: kv[1])[0]
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
    # market's Shin-devig vector, verbatim (no corrections,
    # no blend on top of the market itself, and no
    # popularity-band calibration — that stage was measured
    # on the netkeiba path only).
    final, info = apply_nk_foundation(
        _forecast(), _entry(), ODDS)
    assert info["base"] == "market" and info["pathApplied"]
    assert info["calibration"]["applied"] is False
    expected = shin_devig(ODDS, sorted(STRENGTHS))
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
                           "calibrated", "final"}
    assert info["blendApplied"] is True
    assert all(lean["fired"] for lean in info["leans"].values())
    # The calibration is stamped and is the only post-blend
    # stage: the recorded final vector IS the calibrated
    # vector, and it is the vector the rebuilt forecast
    # carries (rounded).
    assert info["calibration"]["applied"] is True
    assert info["calibration"]["biases"] == \
        list(POPULARITY_BAND_BIASES)
    assert stages["calibrated"] != stages["blended"]
    assert stages["final"] == stages["calibrated"]
    for n, p in stages["final"].items():
        assert abs(_win(final)[n] - round(p, 4)) < 2e-4


def test_band_calibration_direction():
    # The measured correction (favourite/longshot bias):
    # relative to the blended vector, the market favourite
    # (horse 1, band bias +0.1721) gains probability and a
    # 6th-favourite-or-lower runner (horse 8, band bias
    # -0.0983) loses it.
    _, info = apply_nk_foundation(_forecast(), _full_entry(),
                                  ODDS)
    blended = info["stages"]["blended"]
    calibrated = info["stages"]["calibrated"]
    assert calibrated[1] > blended[1]
    assert calibrated[8] < blended[8]


def test_unresolved_circuit_keeps_the_v3_configuration():
    # The conservative default is unchanged in v5: a race
    # whose circuit cannot be resolved runs the v3
    # configuration exactly — temperature 1.1, the arrow
    # fade among the leans, the pooled calibration biases,
    # no scenario stage of either kind.
    entry = _full_entry()
    _, info = apply_nk_foundation(_forecast(), entry, ODDS)
    assert info["segment"] is None
    assert info["temperature"] == 1.1
    assert set(info["leans"]) == {"pace_arrow", "nk_best",
                                  "course_jockey", "press_cp"}
    assert info["leans"]["pace_arrow"]["fired"] is True
    assert info["scenarioMix"]["applied"] is False
    assert info["labelScenarioMix"]["applied"] is False
    assert set(info["stages"]) == {"nkBase", "corrected",
                                   "blended", "calibrated",
                                   "final"}
    assert info["calibration"]["biases"] == \
        list(POPULARITY_BAND_BIASES)
    assert info["calibration"]["fit"] == "pooled-fit"


def test_jra_circuit_runs_combo5():
    # The v5 JRA configuration (beat-market-jra combo5):
    # the v3 leans plus the press_all aggregate at 0.30,
    # the pace-label scenario mixture after the leans,
    # the field-size temperature (this field has 8
    # runners, so 1.0), and the pooled calibration biases.
    # The full entry carries no paceLabel, so the label
    # mixture runs symmetric (t=0, pi in thirds) — the
    # measured construction for a missing label.
    entry = _full_entry()
    final, info = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), entry, ODDS)
    assert info["segment"] == "jra"
    assert info["temperature"] == 1.0
    assert set(info["leans"]) == {"pace_arrow", "nk_best",
                                  "course_jockey", "press_cp",
                                  "press_all"}
    assert info["leans"]["press_all"] == \
        {"weight": 0.30, "fired": True}
    assert info["scenarioMix"]["applied"] is False
    lab = info["labelScenarioMix"]
    assert lab["applied"] is True and lab["label"] is None
    assert lab["beta"] == 2.6 and lab["w"] == 1.5
    assert lab["pi"] == [round(1 / 3, 6)] * 3
    assert set(info["stages"]) == {"nkBase", "corrected",
                                   "scenario", "blended",
                                   "calibrated", "final"}
    assert info["stages"]["final"] == info["stages"]["calibrated"]
    assert info["calibration"]["biases"] == \
        list(POPULARITY_BAND_BIASES)
    assert info["calibration"]["fit"] == "pooled-fit"
    assert info["calibration"]["segment"] == "jra"
    explicit, info2 = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), entry, ODDS,
        segment="jra_flat")
    assert info2["segment"] == "jra"
    assert _win(explicit) == _win(final)
    assert info2["stages"] == info["stages"]


def test_jra_label_scenario_direction():
    # An H label tilts the mixture to the high-pace
    # scenario: the front-runner (start pct 0.1) loses at
    # the scenario stage relative to an S label, and the
    # back-marker (start pct 0.8) gains — and vice versa.
    entry_h = _full_entry()
    entry_h["paceLabel"] = "H"
    entry_s = _full_entry()
    entry_s["paceLabel"] = "S"
    _, info_h = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), entry_h, ODDS)
    _, info_s = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), entry_s, ODDS)
    assert info_h["labelScenarioMix"]["label"] == "H"
    assert info_s["labelScenarioMix"]["label"] == "S"
    assert info_h["stages"]["corrected"] == \
        info_s["stages"]["corrected"]
    assert info_h["stages"]["scenario"][1] < \
        info_s["stages"]["scenario"][1]
    assert info_h["stages"]["scenario"][8] > \
        info_s["stages"]["scenario"][8]


def _field_forecast(count, race_id):
    strengths = {n: 1.0 / count
                 for n in range(1, count + 1)}
    runners = tuple(
        RunnerForecast(
            number=n, name=f"horse-{n}", ability_score=50.0,
            strength=strengths[n], pace_adjustment=1.0,
            pace_reasons=(), p_win=strengths[n], p_top2=None,
            p_top3=None, mark="", status="ok")
        for n in sorted(strengths))
    return RaceForecast(race_id, 3.0, "uncalibrated",
                        runners, "ok")


def _field_entry(count):
    horses = {}
    for n in range(1, count + 1):
        horses[str(n)] = {
            "odds": {"forecastWin": 2.0 + n},
            "pace": {"start": {"pct": n / (count + 1.0)},
                     "corner4": {"pct": 0.5}}}
    return {"horses": horses}


def _field_odds(count):
    return {n: 2.0 + n for n in range(1, count + 1)}


def test_jra_temperature_splits_by_field_size():
    # <=13 runners -> 1.0; >=14 runners -> 1.25 (the
    # fs-tau point selected on every fold).
    _, info13 = apply_nk_foundation(
        _field_forecast(13, "jra-2026-11-28-東京-04"),
        _field_entry(13), _field_odds(13))
    assert info13["temperature"] == 1.0
    _, info14 = apply_nk_foundation(
        _field_forecast(14, "jra-2026-11-28-東京-04"),
        _field_entry(14), _field_odds(14))
    assert info14["temperature"] == 1.25


def test_jra_press_all_aggregate_passes_the_gate():
    # No CP column anywhere: press_cp cannot fire, but
    # the aggregate over the other tipsters covers the
    # field and fires. The signal is the point sum over
    # every tipster's mark.
    horses = {}
    top_marks = ("◎", "○", "▲", "△", "☆")
    for i, n in enumerate(sorted(STRENGTHS)):
        horses[str(n)] = {
            "odds": {"forecastWin": NK_ODDS[n]},
            "press": {"marks": {"本紙": top_marks[i % 5],
                                "AI予想": "○",
                                "厩舎": "▲"}}}
    entry = {"horses": horses}
    signal = press_all_signal(entry)
    assert signal[1] == 12 and signal[2] == 11
    assert signal[5] == 8
    _, info = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), entry, ODDS)
    assert info["leans"]["press_cp"]["fired"] is False
    assert info["leans"]["press_all"]["fired"] is True
    assert info["coverage"]["press_all"] == 8
    # A horse with no press block at all is absent; a
    # horse with a press block but no marks scores 0.
    sparse = {"horses": {"1": {"press": {"marks": {}}},
                         "2": {}}}
    assert press_all_signal(sparse) == {1: 0}


def test_jra_ignores_the_history_argument():
    # The history leans are NAR-only: a JRA race produces
    # the identical stages with and without history.
    history = _history()
    plain, _ = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), _full_entry(),
        ODDS)
    with_history, info = apply_nk_foundation(
        _forecast("jra-2026-11-28-東京-04"), _full_entry(),
        ODDS, history=history)
    assert "rotation_bucket" not in info["leans"]
    assert _win(plain) == _win(with_history)


def test_nar_circuit_runs_the_winning_configuration():
    # The measured winner, NAR only: temperature 1.25, the
    # pace scenario mixture replaces the arrow fade (the
    # other three leans unchanged), and the calibration
    # takes the per-circuit NAR biases. v5 adds the two
    # history leans to the recorded lean set — with no
    # history argument they are present in the stamp with
    # zero coverage and do not fire — and strengthens the
    # mixture to w=2.0. The full entry's start percentiles
    # are 0.1..0.8, so L = 2 runners are at <= 0.25.
    final, info = apply_nk_foundation(
        _forecast("nar-2026-11-28-高知-12"), _full_entry(),
        ODDS)
    assert info["segment"] == "nar"
    assert info["temperature"] == 1.25
    assert "pace_arrow" not in info["leans"]
    assert set(info["leans"]) == {"nk_best", "course_jockey",
                                  "press_cp",
                                  "rotation_bucket",
                                  "venue_avgfin"}
    for name in ("nk_best", "course_jockey", "press_cp"):
        assert info["leans"][name]["fired"] is True
    for name in ("rotation_bucket", "venue_avgfin"):
        assert info["leans"][name] == \
            {"weight": 0.10, "fired": False}
        assert info["coverage"][name] == 0
    assert info["labelScenarioMix"]["applied"] is False
    assert info["scenarioMix"]["applied"] is True
    assert info["scenarioMix"]["beta"] == 2.6
    assert info["scenarioMix"]["w"] == 2.0
    assert info["scenarioMix"]["leaders"] == 2
    assert set(info["stages"]) == {"nkBase", "corrected",
                                   "scenario", "blended",
                                   "calibrated", "final"}
    assert info["stages"]["final"] == info["stages"]["calibrated"]
    assert info["calibration"]["biases"] == \
        list(POPULARITY_BAND_BIASES_NAR)
    # The constants themselves are the measurement's
    # published per-circuit fit (shrunk x0.5) — pinned
    # literally so a silent change to the pooled values
    # fails here.
    assert POPULARITY_BAND_BIASES_NAR == \
        (0.180, 0.009, -0.165, -0.024)
    assert info["calibration"]["fit"] == "nar-fit"
    assert info["calibration"]["segment"] == "nar"
    for n, p in info["stages"]["final"].items():
        assert abs(_win(final)[n] - round(p, 4)) < 2e-4


def test_nar_scenario_mix_direction():
    # Few front-runners (L=1): the slow scenario dominates,
    # so the lone front-runner gains and a back-marker
    # loses at the scenario stage. Many front-runners
    # (L=4): the high scenario dominates and the same
    # front-runner loses instead.
    slow = {n: (0.90, 0.5) for n in STRENGTHS}
    slow[1] = (0.10, 0.5)
    _, info = apply_nk_foundation(
        _forecast("nar-2026-11-28-高知-12"),
        _full_entry(pace=slow), ODDS)
    assert info["scenarioMix"]["leaders"] == 1
    assert info["stages"]["scenario"][1] > \
        info["stages"]["corrected"][1]
    assert info["stages"]["scenario"][8] < \
        info["stages"]["corrected"][8]
    high = {n: (0.90, 0.5) for n in STRENGTHS}
    for n in (1, 2, 3, 4):
        high[n] = (0.10, 0.5)
    _, info = apply_nk_foundation(
        _forecast("nar-2026-11-28-高知-12"),
        _full_entry(pace=high), ODDS)
    assert info["scenarioMix"]["leaders"] == 4
    assert info["stages"]["scenario"][1] < \
        info["stages"]["corrected"][1]


def test_nar_scenario_mix_coverage_gate():
    # Start percentiles for only 3 of 8 runners (37.5%):
    # the mixture must not fire and the scenario stage is
    # the corrected vector untouched.
    sparse = {n: (0.10, 0.5) for n in (1, 2, 3)}
    _, info = apply_nk_foundation(
        _forecast("nar-2026-11-28-高知-12"),
        _full_entry(pace=sparse), ODDS)
    assert info["scenarioMix"]["applied"] is False
    assert info["scenarioMix"]["coverage"] == 3
    assert info["stages"]["scenario"] == \
        info["stages"]["corrected"]


def _run(day, track="高知", finish=5, field=12):
    return {"date": day, "track": track, "raceNumber": 3,
            "distance": 1400, "finish": finish,
            "fieldSize": field}


def _history():
    # Race: 2026-11-28 at 高知. Horse 1 ran 8 days ago at
    # the venue and finished 2nd of 12 (bucket +1, strong
    # venue figure); horse 2 ran 88 days ago at the venue
    # and finished 11th of 12 (bucket -1, weak venue
    # figure); the rest ran 18 days ago at the venue,
    # mid-pack (bucket 0, middling venue figure).
    horses = {}
    for n in sorted(STRENGTHS):
        if n == 1:
            runs = [_run("2026-11-20", finish=2)]
        elif n == 2:
            runs = [_run("2026-09-01", finish=11)]
        else:
            runs = [_run("2026-11-10", finish=6)]
        horses[str(n)] = runs
    return {"date": "2026-11-28", "venue": "高知",
            "horses": horses}


def test_nar_history_leans_fire_and_move_the_vector():
    with_h, info = apply_nk_foundation(
        _forecast("nar-2026-11-28-高知-12"), _full_entry(),
        ODDS, history=_history())
    assert info["leans"]["rotation_bucket"] == \
        {"weight": 0.10, "fired": True}
    assert info["leans"]["venue_avgfin"] == \
        {"weight": 0.10, "fired": True}
    assert info["coverage"]["rotation_bucket"] == 8
    assert info["coverage"]["venue_avgfin"] == 8
    without_h, _ = apply_nk_foundation(
        _forecast("nar-2026-11-28-高知-12"), _full_entry(),
        ODDS)
    # The short-rotation, venue-proven horse gains; the
    # long-absent, venue-poor horse loses.
    assert _win(with_h)[1] > _win(without_h)[1]
    assert _win(with_h)[2] < _win(without_h)[2]


def test_rotation_bucket_boundaries():
    def hist(day):
        return {"date": "2026-11-28", "venue": "高知",
                "horses": {"1": [_run(day)]}}
    assert rotation_bucket_signal(hist("2026-11-14")) == \
        {1: 1.0}   # 14 days: short rotation
    assert rotation_bucket_signal(hist("2026-11-13")) == \
        {1: 0.0}   # 15 days
    assert rotation_bucket_signal(hist("2026-10-24")) == \
        {1: 0.0}   # 35 days
    assert rotation_bucket_signal(hist("2026-10-23")) == \
        {1: -1.0}  # 36 days: long absence


def test_history_uses_only_pre_race_runs():
    # A run ON the race date (or later) is not a past run:
    # the horse is absent from both signals — nothing
    # from the day itself can leak into a lean.
    same_day = {"date": "2026-11-28", "venue": "高知",
                "horses": {"1": [_run("2026-11-28")],
                           "2": [_run("2026-12-05")]}}
    assert rotation_bucket_signal(same_day) == {}
    assert venue_avgfin_signal(same_day) == {}
    # A duplicate of the same race (the detail carries it
    # in both run lists) counts once for the venue mean,
    # and the rotation reads the LATEST pre-race run.
    dup = _run("2026-11-20", finish=3, field=10)
    history = {"date": "2026-11-28", "venue": "高知",
               "horses": {"1": [dup, dict(dup),
                                _run("2026-11-05", finish=9,
                                     field=10)]}}
    venue = venue_avgfin_signal(history)
    assert abs(venue[1] - (-(0.3 + 0.9) / 2)) < 1e-12
    assert rotation_bucket_signal(history) == {1: 1.0}
    # Runs at another track count for the rotation but
    # not for the venue figure.
    away = {"date": "2026-11-28", "venue": "高知",
            "horses": {"1": [_run("2026-11-20",
                                  track="佐賀")]}}
    assert rotation_bucket_signal(away) == {1: 1.0}
    assert venue_avgfin_signal(away) == {}
