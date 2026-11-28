"""Debut lane (2026-11-28): first-starters-only races publish on
the market base with the collected materials layered on.

Until this lane existed, a debut race never published at all: the
ability layer scores nobody (every runner is a first starter),
the v1 fallback answers "insufficient-scored-runners", and the
build rejects the race — even though the collection carries
exactly the material that can price a debut runner (training
grades, press marks, stable comments, forecast odds).

These tests pin the lane's contract:

- the base vector is the market itself (inverse win odds,
  normalised), built ONLY when every active runner carries a
  real win odd (> 1.0) — partial coverage defers, never imputes;
- the join keys are the race card's own horse numbers (the
  normalised race record), never the v8 extras' keys;
- the materials adjustment applies through the existing
  apply_nk_materials path, so a graded runner moves off her
  market price in the grade's direction and an ungraded runner
  keeps her market share of the base;
- the override guard does NOT apply (it is defined on the v9b
  vector; the debut base already is the market);
- the labelling stays honest: abilityLane "debut-market",
  abilityModelVersion "arvexq-debut-market-prior", every
  runner's ability score null, and probabilityStatus
  "uncalibrated-prior" — never the v9b calibrated label;
- the lane is strictly segment-scoped: a flat race with no
  scored runners still fails exactly as before;
- a frozen debut publication qualifies for the nk-materials
  upgrade on the jumps path's rules, so materials collected
  after first publication still reach a pre-post race.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from rewrite.analysis.forecast import (
    DEBUT_MARKET_INCOMPLETE, RaceForecast, forecast_debut_market)
from rewrite.analysis.clean_forecast import (
    CLEAN_FORECAST_VERSION, power_devig)
from rewrite.analysis.nk_materials import apply_nk_materials
from rewrite.data.normalize import Obs, RaceRecord, RunnerRecord, obs
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.safety.contracts import Segment
from scripts.arvexq_rewrite_publish import (
    DEBUT_ABILITY_MODEL_VERSION, DEBUT_LANE, _nk_materials_upgrade_info,
    build_publish_detail)

JST = ZoneInfo("Asia/Tokyo")
RACE_ID = "jra-2026-11-28-東京-04"
DATE = "2026-11-28"
POST = "11:20"
NOW = datetime(2026, 11, 28, 9, 0, tzinfo=JST)  # 140 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ",
         4: "エエエ", 5: "オオオ", 6: "カカカ"}
ODDS = {1: 2.0, 2: 3.5, 3: 5.0, 4: 8.0, 5: 15.0, 6: 30.0}
RECEIPT = "a" * 64


def fabricated_race(odds=ODDS, *, segment=Segment.DEBUT,
                    title="2歳新馬", scratched=()) -> RaceRecord:
    missing = Obs(None, "test", "not_captured")
    runners = []
    for number in (1, 2, 3, 4, 5, 6):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"), frame_number=missing,
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=obs(odds[number], "test")
            if odds and number in odds else missing,
            scratched=number in scratched, past_runs=()))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("中央", "test"),
        track="東京", race_number=obs(4, "test"),
        title=obs(title, "test"), start_time=obs(POST, "test"),
        distance=obs(1400, "test"), surface=obs("ダート", "test"),
        weather=missing, condition=missing, updated_at=missing,
        segment=segment, source="test", runners=tuple(runners))


def market_base(odds):
    inverse = {n: 1.0 / o for n, o in odds.items()}
    total = sum(inverse.values())
    return {n: v / total for n, v in inverse.items()}


class DebutMarketForecastTests(TestCase):
    def test_complete_market_builds_market_base(self):
        forecast = forecast_debut_market(fabricated_race(), ODDS)
        self.assertEqual(forecast.status, "ok")
        self.assertEqual(forecast.probability_status,
                         "uncalibrated-prior")
        base = market_base(ODDS)
        by_number = {r.number: r for r in forecast.runners}
        for number, expected in base.items():
            runner = by_number[number]
            self.assertAlmostEqual(runner.p_win, expected, places=3)
            self.assertIsNone(runner.ability_score)
            self.assertEqual(runner.status, "market-prior")
        total = sum(r.p_win for r in forecast.runners)
        self.assertAlmostEqual(total, 1.0, places=3)
        # Five marks, win-probability order: the market favourite
        # carries ◎ and the longest price carries none.
        marks = {r.number: r.mark for r in forecast.runners if r.mark}
        self.assertEqual(len(marks), 5)
        self.assertEqual(by_number[1].mark, "◎")
        self.assertEqual(by_number[6].mark, "")

    def test_partial_market_is_incomplete(self):
        odds = dict(ODDS)
        del odds[6]
        forecast = forecast_debut_market(fabricated_race(odds), odds)
        self.assertEqual(forecast.status, DEBUT_MARKET_INCOMPLETE)
        self.assertTrue(all(r.p_win is None for r in forecast.runners))

    def test_odds_of_exactly_one_are_not_a_market(self):
        odds = dict(ODDS)
        odds[3] = 1.0
        forecast = forecast_debut_market(fabricated_race(odds), odds)
        self.assertEqual(forecast.status, DEBUT_MARKET_INCOMPLETE)

    def test_no_odds_at_all_is_incomplete(self):
        forecast = forecast_debut_market(fabricated_race(None), {})
        self.assertEqual(forecast.status, DEBUT_MARKET_INCOMPLETE)

    def test_scratched_runner_needs_no_odds_and_gets_no_probability(self):
        odds = dict(ODDS)
        del odds[6]
        race = fabricated_race(odds, scratched=(6,))
        forecast = forecast_debut_market(race, odds)
        self.assertEqual(forecast.status, "ok")
        by_number = {r.number: r for r in forecast.runners}
        self.assertIsNone(by_number[6].p_win)
        self.assertEqual(by_number[6].status, "scratched")
        base = market_base(odds)
        self.assertAlmostEqual(by_number[1].p_win, base[1], places=3)

    def test_fewer_than_three_active_runners_is_incomplete(self):
        race = fabricated_race(scratched=(3, 4, 5, 6))
        forecast = forecast_debut_market(race, ODDS)
        self.assertEqual(forecast.status, DEBUT_MARKET_INCOMPLETE)


def grade_entry() -> dict:
    return {"netkeibaRaceId": "202605050704",
            "courseAnalysis": None,
            "horses": {1: {"grade": "B"},
                       2: {"grade": "C"},
                       3: {"grade": "B"},
                       4: {"grade": "C"}}}


class DebutMaterialsTests(TestCase):
    def test_grade_term_moves_probabilities_in_grade_direction(self):
        # Equal odds: the base is flat, so any movement is the
        # grade term's alone. B must finish above C (the standing
        # measurement on the 2026-11-21 debut fields: grade is
        # monotone in finishing position).
        flat_odds = {n: 6.0 for n in NAMES}
        base = forecast_debut_market(fabricated_race(flat_odds),
                                     flat_odds)
        self.assertEqual(base.status, "ok")
        adjusted, info = apply_nk_materials(
            base, grade_entry(), {}, segment="debut")
        self.assertTrue(info["applied"])
        self.assertIn("grade", info["terms"])
        by_number = {r.number: r for r in adjusted.runners}
        self.assertGreater(by_number[1].p_win, by_number[2].p_win)
        self.assertGreater(by_number[1].p_win, 1.0 / 6.0)
        self.assertLess(by_number[2].p_win, 1.0 / 6.0)
        # An ungraded runner is never shifted by the term: she
        # keeps her base share up to the renormalisation the
        # graded runners' movement implies, and stays level with
        # the other ungraded runner.
        self.assertAlmostEqual(by_number[5].p_win,
                               by_number[6].p_win, places=6)
        # The lane's honest labelling survives the adjustment.
        self.assertEqual(adjusted.probability_status,
                         "uncalibrated-prior")
        self.assertTrue(all(r.ability_score is None
                            for r in adjusted.runners))
        self.assertTrue(all(r.status == "market-prior"
                            for r in adjusted.runners))

    def test_no_materials_keeps_the_base_object(self):
        base = forecast_debut_market(fabricated_race(), ODDS)
        adjusted, info = apply_nk_materials(
            base, {"netkeibaRaceId": None, "horses": {}}, {},
            segment="debut")
        self.assertFalse(info["applied"])
        self.assertIs(adjusted, base)


def fresh_detail(odds=ODDS) -> dict:
    horses = []
    for number in (1, 2, 3, 4, 5, 6):
        horse = {"horseNumber": number, "name": NAMES[number]}
        if odds and number in odds:
            horse["winOdds"] = odds[number]
        horses.append(horse)
    return {"id": RACE_ID, "date": DATE, "scheduledStartTime": POST,
            "title": "2歳新馬", "circuit": "中央", "track": "東京",
            "horses": horses}


def summary() -> dict:
    return {"race_id": RACE_ID, "id": RACE_ID}


class DebutBuildTests(TestCase):
    def _build(self, detail, race, materials):
        with patch("scripts.arvexq_rewrite_publish.normalize_race",
                   return_value=race), \
                patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                      return_value=materials):
            return build_publish_detail(detail, summary(), NOW)

    def test_first_publication_on_complete_market_with_materials(self):
        materials = {RACE_ID: grade_entry()}
        new, receipt = self._build(
            fresh_detail(), fabricated_race(), materials)
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["abilityLane"], DEBUT_LANE)
        self.assertEqual(marker["debutMarket"]["base"],
                         "win-odds-market")
        self.assertEqual(marker["debutMarket"]["activeRunners"], 6)
        self.assertEqual(marker["debutMarket"]["oddsCoveredRunners"], 6)
        # The foundation stamp landed; the override guard is
        # a v9b-lane stage and never stamps a debut
        # publication. Clean-forecast-v2 (2026-11-28 rebuild):
        # the debut entry carries no forecast odds, so the
        # foundation stands on the market base, and the grade
        # material the publication stood on is recorded in
        # the stamp's entryFingerprint — the retired grade
        # term no longer stands in the probability path.
        self.assertTrue(marker["nkMaterials"]["applied"])
        self.assertEqual(marker["nkMaterials"]["version"],
                         CLEAN_FORECAST_VERSION)
        self.assertEqual(marker["nkMaterials"]["base"], "market")
        self.assertEqual(
            marker["nkMaterials"]["entryFingerprint"]["grade"], 4)
        self.assertNotIn("terms", marker["nkMaterials"])
        self.assertNotIn("overrideGuard", marker)
        unified = new["unifiedForecast"]
        self.assertEqual(unified["abilityModelVersion"],
                         DEBUT_ABILITY_MODEL_VERSION)
        self.assertEqual(unified["probabilityStatus"],
                         "uncalibrated-prior")
        self.assertEqual(new["predictionStatus"], "ready")
        self.assertEqual(len(new["predictionMarks"]), 5)
        # Probabilities stand on the market alone: they are
        # exactly the foundation's market base (the power
        # devig of the win odds). The grade material is
        # collected and recorded (see the fingerprint above)
        # but, since the clean-forecast-v2 rebuild, no longer
        # shifts a debut probability in its direction.
        win = new["prediction"]["stages"]["probability"]["value"]["win"]
        base = power_devig(ODDS, sorted(ODDS))
        for number in ODDS:
            self.assertAlmostEqual(win[number], base[number],
                                   places=3)

    def test_first_publication_without_materials_is_market_only(self):
        new, receipt = self._build(fresh_detail(), fabricated_race(), {})
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["abilityLane"], DEBUT_LANE)
        self.assertNotIn("nkMaterials", marker)
        win = new["prediction"]["stages"]["probability"]["value"]["win"]
        base = market_base(ODDS)
        for number, expected in base.items():
            self.assertAlmostEqual(win[number], expected, places=3)

    def test_incomplete_market_defers(self):
        odds = dict(ODDS)
        del odds[6]
        new, reason = self._build(
            fresh_detail(odds), fabricated_race(odds), {})
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("deferred:"), reason)
        self.assertIn("debut market not complete", reason)

    def test_flat_segment_is_not_routed_to_the_debut_lane(self):
        # A flat race with no scored runners keeps the exact
        # pre-lane behaviour: the v1 fallback answers
        # insufficient-scored-runners and the build rejects.
        race = fabricated_race(segment=Segment.JRA_FLAT,
                               title="2歳未勝利")
        not_ok = RaceForecast(RACE_ID, 3.0, "uncalibrated-prior", (),
                              "insufficient-scored-runners")
        extras = {RACE_ID: {"segment": "jra_flat",
                            "extras": {"1": {"elo": 1500.0}}}}
        with patch("scripts.arvexq_rewrite_publish.normalize_race",
                   return_value=race), \
                patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                      return_value=extras), \
                patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                      return_value=not_ok):
            new, reason = build_publish_detail(
                fresh_detail(), summary(), NOW)
        self.assertIsNone(new)
        self.assertEqual(
            reason, "forecast not ok: insufficient-scored-runners")


def stored_debut_detail(*, nk_stamp=None) -> dict:
    horses = [{"horseNumber": n, "name": NAMES[n], "winOdds": ODDS[n]}
              for n in (1, 2, 3, 4, 5, 6)]
    marker = {"modelVersion": MODEL_VERSION,
              "publishedAt": "2026-11-28T09:00:00+09:00",
              "receiptSha256": RECEIPT,
              "abilityLane": DEBUT_LANE,
              "debutMarket": {"base": "win-odds-market",
                              "activeRunners": 6,
                              "oddsCoveredRunners": 6}}
    if nk_stamp is not None:
        marker["nkMaterials"] = nk_stamp
    roster = [{"horseNumber": h["horseNumber"], "name": h["name"]}
              for h in horses]
    return {"id": RACE_ID, "date": DATE, "scheduledStartTime": POST,
            "title": "2歳新馬", "circuit": "中央", "track": "東京",
            "predictionStatus": "ready",
            "predictionModelVersion": MODEL_VERSION,
            "preparedMeta": {"rewritePublish": marker},
            "unifiedForecast": {"receiptSha256": RECEIPT,
                                "roster": roster},
            "horses": horses}


class DebutNkUpgradeQualificationTests(TestCase):
    def test_unstamped_debut_race_qualifies_when_materials_land(self):
        materials = {RACE_ID: grade_entry()}
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value=materials):
            info = _nk_materials_upgrade_info(
                stored_debut_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["previousAbilityLane"], DEBUT_LANE)

    def test_debut_race_without_materials_does_not_qualify(self):
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value={}):
            info = _nk_materials_upgrade_info(
                stored_debut_detail(), NOW)
        self.assertIsNone(info)

    def test_thin_materials_do_not_qualify(self):
        # Below the any-family threshold (3 horses) no z-score
        # term can exist; the frozen market base stays.
        entry = {"netkeibaRaceId": "202605050704",
                 "courseAnalysis": None,
                 "horses": {1: {"grade": "B"}, 2: {"grade": "C"}}}
        with patch("scripts.arvexq_rewrite_publish._load_nk_materials",
                   return_value={RACE_ID: entry}):
            info = _nk_materials_upgrade_info(
                stored_debut_detail(), NOW)
        self.assertIsNone(info)
