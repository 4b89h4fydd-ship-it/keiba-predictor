"""Bias-pace wiring tests (2026-11-19, nk-materials-v12).

The same-day bias read (rewrite/analysis/bias_pace.py — its
own module tests live in test_bias_pace.py) reaches the
forecast: the publish lane computes the day's bias from the
card's already-final races and overlays it on the race's
netkeiba pace forecast, and the nk-materials adapter applies
the overlay as the bias_pace term — a post-integrate logit
shift at the +0.10 cap times the RAW adjustment (the
adjustment already carries the S/(S+2) shrinkage, so the
term weakens automatically early on a card).

These tests pin:
  - the adapter term's direction, stamp-side records
    (terms / coverage / biasPace / biasPaceTrial / weights
    label) and its inertness when the bias is unmeasurable
    or no overlay is handed in (v11 behaviour);
  - the strength weakening: identical raw bias at S=1 moves
    the probabilities less than at S=8;
  - the lane helpers: snapshots only for FINAL results, and
    the overlay's leak filter (a later same-track race and
    an earlier other-track race never enter the read);
  - the build: the detail's biasProvenance.estimated and
    biasPace block carry the real read, and a build
    without day_races stamps none of it. Since the
    clean-forecast-v2 rebuild (2026-11-28) the read is
    display-only at build level: the foundation stamp
    carries no bias term and the published probabilities
    do not move with the read. The adapter-level term
    above remains pinned because the retired adapter is
    still the record the historical stamps were written
    by; the build tests pin the new separation.
"""
from __future__ import annotations

import math
from unittest import TestCase
from unittest.mock import patch

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.analysis.bias_pace import (
    compute_same_day_bias, overlay_bias_on_pace)
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.nk_materials import (
    NK_BIAS_PACE_LABEL, NK_BIAS_PACE_TRIAL, apply_nk_materials,
    parse_materials_payload)
from scripts.arvexq_rewrite_publish import (
    _bias_pace_overlay, _day_race_snapshot, build_publish_detail)
from tests.test_nk_materials import (
    DATE, EXTRAS, NAMES, NOW, RACE_ID,
    fabricated_race, fresh_detail, v9b_like_forecast)

STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}
# Forecast positions for the target race: horse 5 is the
# forecast front-runner, horse 1 the forecast back-marker.
PACE_PCTS = {1: 0.9, 2: 0.7, 3: 0.5, 4: 0.3, 5: 0.1}


def _forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=s, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "calibrated",
                        tuple(runners), "ok")


def _entry(with_pace=True):
    horses = {}
    for n in NAMES:
        horse = {"nk_best": None, "nk_avg5": 60, "nk_dist": None,
                 "nk_course": None, "nk_recent": None}
        if with_pace:
            pct = PACE_PCTS[n]
            horse["pace"] = {
                phase: {"rank": int(pct * 5) or 1, "pct": pct}
                for phase in ("start", "corner3", "corner4")}
        horses[str(n)] = horse
    payload = {"version": "nk-materials-v12", "date": DATE,
               "races": {RACE_ID: {
                   "netkeibaRaceId": "202646111701",
                   "horses": horses, "courseAnalysis": None}}}
    return parse_materials_payload(payload)[RACE_ID]


def _source_race(race_no, start_time, date=DATE, track="金沢"):
    """A 10-runner final whose first-corner leaders swept the
    top 3 (raw front/back bias +1.0) while the inner and outer
    number groups both drew blanks (raw inside/outside 0.0).

    number -> corner1: the front three corners are carried by
    the middle numbers (4, 5, 6), so the number groups stay
    neutral while the corner groups separate completely."""
    corner_of = {1: 7, 2: 8, 3: 9, 4: 1, 5: 2, 6: 3, 7: 4,
                 8: 5, 9: 6, 10: 10}
    finish_of_corner = {c: c for c in range(1, 11)}
    finishers = []
    for number in range(1, 11):
        corner = corner_of[number]
        finishers.append({
            "horseNumber": number,
            "finish": finish_of_corner[corner],
            "cornerPositions": [corner, corner, corner]})
    return {"date": date, "track": track, "raceNo": race_no,
            "startTime": start_time, "finishers": finishers}


def _overlay_for(day_races, entry=None, target=None):
    entry = entry if entry is not None else _entry()
    target = target or {"date": DATE, "track": "金沢",
                        "raceNo": 9, "startTime": "20:40"}
    bias = compute_same_day_bias(target, day_races)
    positions = {n: h["pace"] for n, h in entry["horses"].items()
                 if h.get("pace")}
    return overlay_bias_on_pace(bias, positions, 5)


def _win(forecast, number):
    return next(r.p_win for r in forecast.runners
                if r.number == number)


class BiasPaceAdapterTests(TestCase):
    def test_front_bias_lifts_the_forecast_front_runner(self):
        overlay = _overlay_for([_source_race(1, "18:00")])
        self.assertTrue(overlay["available"])
        self.assertEqual(overlay["bias"]["sampleRaces"], 1)
        base, base_info = apply_nk_materials(_forecast(), _entry())
        adj, info = apply_nk_materials(
            _forecast(), _entry(), bias_overlay=overlay)
        self.assertIn("bias_pace", info["terms"])
        self.assertEqual(info["coverage"]["bias_pace"], 5)
        self.assertEqual(info["biasPaceTrial"], NK_BIAS_PACE_TRIAL)
        self.assertIn(NK_BIAS_PACE_LABEL, info["weights"])
        self.assertEqual(info["biasPace"]["sampleRaces"], 1)
        self.assertAlmostEqual(info["biasPace"]["frontBack"],
                               1.0 / 3.0)
        # Horse 5 (forecast front) gains, horse 1 (forecast
        # back) loses, against the no-overlay application.
        self.assertGreater(_win(adj, 5), _win(base, 5))
        self.assertLess(_win(adj, 1), _win(base, 1))

    def test_unmeasurable_bias_is_inert_but_recorded(self):
        overlay = _overlay_for([])
        self.assertFalse(overlay["available"])
        base, _ = apply_nk_materials(_forecast(), _entry())
        adj, info = apply_nk_materials(
            _forecast(), _entry(), bias_overlay=overlay)
        self.assertNotIn("bias_pace", info.get("terms") or [])
        self.assertNotIn("biasPaceTrial", info)
        self.assertFalse(info["biasPace"]["available"])
        self.assertEqual(info["biasPace"]["sampleRaces"], 0)
        for n in NAMES:
            self.assertAlmostEqual(_win(adj, n), _win(base, n))

    def test_no_overlay_is_v11_behaviour(self):
        _, info = apply_nk_materials(_forecast(), _entry())
        self.assertNotIn("biasPace", info)
        self.assertEqual(info["coverage"]["bias_pace"], 0)

    def test_strength_weakens_the_term(self):
        # The same raw bias (+1.0) read from 1 source race
        # (strength 1/3) must move the probabilities less
        # than the same read from 8 source races (strength
        # 0.8): the shrinkage rides inside the adjustment.
        base, _ = apply_nk_materials(_forecast(), _entry())
        one = _overlay_for([_source_race(1, "18:00")])
        many = _overlay_for(
            [_source_race(i, f"1{i}:00") for i in range(1, 9)],
            target={"date": DATE, "track": "金沢", "raceNo": 12,
                    "startTime": "23:40"})
        self.assertEqual(many["bias"]["sampleRaces"], 8)
        adj_one, _ = apply_nk_materials(
            _forecast(), _entry(), bias_overlay=one)
        adj_many, _ = apply_nk_materials(
            _forecast(), _entry(), bias_overlay=many)
        shift_one = abs(math.log(_win(adj_one, 5) / _win(base, 5)))
        shift_many = abs(math.log(_win(adj_many, 5)
                                  / _win(base, 5)))
        self.assertGreater(shift_one, 0.0)
        self.assertGreater(shift_many, shift_one)


class LaneHelperTests(TestCase):
    def test_snapshot_only_for_final_results(self):
        summary = {"race_date": DATE, "track": "金沢",
                   "race_no": 3, "start_time": "18:00"}
        detail = {"date": DATE, "track": "金沢", "raceNumber": 3,
                  "result": {"status": "確定", "finishers": [
                      {"horseNumber": 1, "finish": 1,
                       "cornerPositions": [1, 1]}]}}
        snap = _day_race_snapshot(summary, detail)
        self.assertIsNotNone(snap)
        self.assertEqual(snap["track"], "金沢")
        self.assertEqual(snap["raceNo"], 3)
        self.assertEqual(snap["finishers"][0]["cornerPositions"],
                         [1, 1])
        # A provisional result (partial finishers) never feeds
        # the pools; neither does a race without a result.
        detail["result"]["status"] = "速報"
        self.assertIsNone(_day_race_snapshot(summary, detail))
        self.assertIsNone(_day_race_snapshot(summary, {"date": DATE}))

    def test_overlay_never_reads_later_or_other_track_races(self):
        entry = _entry()
        summary = {"track": "金沢", "race_no": 9,
                   "start_time": "20:40"}
        old = {"track": "金沢", "raceNumber": 9,
               "scheduledStartTime": "20:40"}
        day = [
            # Earlier, same track: the engineered front bias.
            _source_race(1, "18:00"),
            # Later, same track: an extreme opposite card —
            # if it leaked, the read would change.
            _source_race(2, "21:00"),
            # Earlier, another track: never the same card.
            _source_race(3, "18:30", track="大井"),
        ]
        overlay = _bias_pace_overlay(summary, old, DATE, entry,
                                     day, 5)
        self.assertIsNotNone(overlay)
        self.assertTrue(overlay["available"])
        self.assertEqual(overlay["bias"]["sampleRaces"], 1)
        self.assertAlmostEqual(overlay["bias"]["frontBack"],
                               1.0 / 3.0)

    def test_overlay_none_without_snapshots_or_positions(self):
        summary = {"track": "金沢", "race_no": 9,
                   "start_time": "20:40"}
        old = {"track": "金沢", "raceNumber": 9}
        self.assertIsNone(_bias_pace_overlay(
            summary, old, DATE, _entry(), None, 5))
        self.assertIsNone(_bias_pace_overlay(
            summary, old, DATE, _entry(with_pace=False),
            [_source_race(1, "18:00")], 5))


def _build_with_bias(detail, day_races):
    """BuildTests' harness, extended with day_races and a
    materials entry that carries pace positions."""
    payload = {"version": "nk-materials-v12", "date": DATE,
               "races": {RACE_ID: {
                   "netkeibaRaceId": "202646111701",
                   "horses": {str(n): {
                       "nk_best": 60, "nk_avg5": 60,
                       "nk_dist": None, "nk_course": None,
                       "nk_recent": None,
                       "pace": {phase: {"rank": 1, "pct": PACE_PCTS[n]}
                                for phase in ("start", "corner3",
                                              "corner4")}}
                       for n in NAMES},
                   "courseAnalysis": None}}}
    materials = parse_materials_payload(payload)
    ctx = [
        patch("scripts.arvexq_rewrite_publish.normalize_race",
              return_value=fabricated_race()),
        patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
              return_value=v9b_like_forecast()),
        patch("scripts.arvexq_rewrite_publish._load_v8_extras",
              return_value=EXTRAS),
        patch("scripts.arvexq_rewrite_publish._load_nk_materials",
              return_value=materials),
    ]
    for c in ctx:
        c.start()
    try:
        return build_publish_detail(
            detail, {"race_id": RACE_ID, "id": RACE_ID}, NOW,
            day_races=day_races)
    finally:
        for c in reversed(ctx):
            c.stop()


class BiasPaceBuildTests(TestCase):
    DAY = [_source_race(1, "18:00"), _source_race(2, "19:00")]

    def test_build_displays_the_bias_read_and_stamps_no_bias_term(self):
        new, receipt = _build_with_bias(fresh_detail(), self.DAY)
        self.assertIsNotNone(new, receipt)
        stamp = new["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertTrue(stamp["applied"])
        # Clean-forecast-v2 (2026-11-28 rebuild): the bias
        # read no longer stands in the probability path, so
        # the stamp records no bias term, no trial label and
        # no bias block — the stamp is the foundation's alone.
        self.assertEqual(stamp["version"], "clean-forecast-v3")
        self.assertNotIn("terms", stamp)
        self.assertNotIn("biasPace", stamp)
        self.assertNotIn("biasPaceTrial", stamp)
        # Display data: the provenance estimate carries the
        # real read, and the sibling block carries the summary.
        estimated = new["biasProvenance"]["estimated"]
        self.assertAlmostEqual(estimated["frontBack"], 0.5)
        self.assertEqual(estimated["sampleRaces"], 2)
        block = new["biasPace"]
        self.assertTrue(block["available"])
        self.assertIn("front-favourable", block["summary"]["tags"])
        self.assertEqual(block["summary"]["mostAdvantaged"][0], 5)
        self.assertIsNotNone(verified_unified(new))

    def test_build_without_day_races_stamps_no_bias(self):
        new, receipt = _build_with_bias(fresh_detail(), None)
        self.assertIsNotNone(new, receipt)
        stamp = new["preparedMeta"]["rewritePublish"]["nkMaterials"]
        self.assertNotIn("biasPace", stamp)
        self.assertNotIn("biasPaceTrial", stamp)
        self.assertNotIn("terms", stamp)
        self.assertNotIn("biasPace", new)
        self.assertNotIn("biasProvenance", new)

    def test_bias_read_no_longer_moves_the_published_probabilities(self):
        # The bias overlay is display-only since the
        # clean-forecast-v2 rebuild: the read is still
        # computed and shown (see the biasPace block above),
        # but the published probabilities are the
        # foundation's alone, identical with and without the
        # day's earlier races.
        with_bias, _ = _build_with_bias(fresh_detail(), self.DAY)
        without, _ = _build_with_bias(fresh_detail(), None)
        self.assertIn("biasPace", with_bias)
        self.assertNotIn("biasPace", without)
        win_with = with_bias["prediction"]["stages"]["probability"]["value"]["win"]
        win_without = without["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertEqual(win_with, win_without)
