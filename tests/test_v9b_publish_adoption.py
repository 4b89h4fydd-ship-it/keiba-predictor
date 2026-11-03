"""v9b production adoption (2026-11-03): freeze recognition across
the model-version bump and the adoption-day lane upgrade, plus the
production post-processing transform's blend gating.

The transform itself is the shadow lane's definition ported
verbatim (rewrite/analysis/shadow_v9.py); these tests pin the
publish lane's use of it: temperature T = 0.6692 always applies on
the v8 lane, the geometric market blend (w = 0.5) applies only when
win odds exist for every runner in the probability vector, and the
result stays a normalised distribution.

Freeze side: publications stamped under the previous model version
(arvexq-rewrite-v2-elo-speed2) remain this lane's frozen state, and
a race dated 2026-11-04 frozen on the v8 lane is an upgrade source
(reason lane-upgrade-v9b-adoption) while any other date is not.
"""
from __future__ import annotations

from math import fsum
from unittest import TestCase
from unittest.mock import patch

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.shadow_v9 import (
    BLEND_WEIGHT, TEMPERATURE, postprocess_forecast)
from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    PREVIOUS_MODEL_VERSION, _freeze_decision, _lane_upgrade_info)

RECEIPT = "a" * 64


def v8_forecast() -> RaceForecast:
    runners = []
    strengths = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}
    for number, strength in strengths.items():
        runners.append(RunnerForecast(
            number=number, name=f"馬{number}", ability_score=0.5,
            strength=strength, pace_adjustment=1.0, pace_reasons=(),
            p_win=None, p_top2=None, p_top3=None, mark="",
            status="scored"))
    return RaceForecast("nar-2026-11-04-園田-01", 3.0,
                        "uncalibrated-prior", tuple(runners), "ok")


def win_probs(forecast: RaceForecast) -> dict[int, float]:
    return {r.number: r.p_win for r in forecast.runners
            if r.p_win is not None}


class PostprocessGatingTests(TestCase):
    def test_frozen_constants(self):
        self.assertEqual(TEMPERATURE, 0.6692)
        self.assertEqual(BLEND_WEIGHT, 0.5)

    def test_full_odds_blend_applies_and_normalises(self):
        odds = {1: 2.0, 2: 3.0, 3: 5.0, 4: 8.0, 5: 20.0}
        out, info = postprocess_forecast(
            v8_forecast(), arm="v9b", win_odds=odds)
        self.assertTrue(info["blendApplied"])
        probs = win_probs(out)
        self.assertAlmostEqual(fsum(probs.values()), 1.0, places=3)
        # Manual geometric pool of the temperature-scaled base with
        # the market: the favourite's share must move toward the
        # market's (the market rates #1 higher than the model).
        self.assertGreater(probs[1], 0.30)

    def test_missing_odds_fall_back_to_temperature_only(self):
        odds = {1: 2.0, 2: 3.0, 3: 5.0, 4: 8.0}  # #5 missing
        out, info = postprocess_forecast(
            v8_forecast(), arm="v9b", win_odds=odds)
        self.assertFalse(info["blendApplied"])
        probs = win_probs(out)
        self.assertAlmostEqual(fsum(probs.values()), 1.0, places=3)
        # Temperature T < 1 sharpens: the top share grows vs base.
        self.assertGreater(probs[1], 0.30)
        self.assertLess(probs[5], 0.10)

    def test_odds_of_exactly_one_block_the_blend(self):
        odds = {1: 2.0, 2: 3.0, 3: 5.0, 4: 8.0, 5: 1.0}
        _out, info = postprocess_forecast(
            v8_forecast(), arm="v9b", win_odds=odds)
        self.assertFalse(info["blendApplied"])

    def test_no_odds_at_all_is_temperature_only(self):
        out, info = postprocess_forecast(
            v8_forecast(), arm="v9b", win_odds={})
        self.assertFalse(info["blendApplied"])
        self.assertAlmostEqual(
            fsum(win_probs(out).values()), 1.0, places=3)


def stamped_detail(stamp: str, lane: str, date: str) -> dict:
    return {
        "id": f"nar-{date}-園田-01",
        "date": date,
        "scheduledStartTime": "20:50",
        "predictionStatus": "ready",
        "predictionModelVersion": stamp,
        "preparedMeta": {"rewritePublish": {
            "modelVersion": stamp,
            "publishedAt": "2026-11-03T21:05:00+09:00",
            "receiptSha256": RECEIPT,
            "abilityLane": lane}},
        "unifiedForecast": {
            "receiptSha256": RECEIPT,
            "roster": [{"horseNumber": 1, "name": "アアア"},
                       {"horseNumber": 2, "name": "イイイ"},
                       {"horseNumber": 3, "name": "ウウウ"}]},
        "horses": [{"horseNumber": 1, "name": "アアア"},
                   {"horseNumber": 2, "name": "イイイ"},
                   {"horseNumber": 3, "name": "ウウウ"}],
    }


EXTRAS = {"nar-2026-11-04-園田-01": {
    "segment": "nar",
    "extras": {"1": {"elo": 900.0}, "2": {"elo": 850.0}}}}


class VersionBumpFreezeTests(TestCase):
    def test_previous_version_stamp_stays_frozen(self):
        detail = stamped_detail(PREVIOUS_MODEL_VERSION,
                                "v8-elo-speed2", "2026-11-04")
        self.assertEqual(_freeze_decision(detail), ("frozen", RECEIPT))

    def test_current_version_stamp_stays_frozen(self):
        detail = stamped_detail(MODEL_VERSION, "v9b-cal-market",
                                "2026-11-05")
        self.assertEqual(_freeze_decision(detail), ("frozen", RECEIPT))

    def test_mixed_stamps_are_not_frozen(self):
        detail = stamped_detail(PREVIOUS_MODEL_VERSION,
                                "v8-elo-speed2", "2026-11-04")
        detail["predictionModelVersion"] = "arvexq-stage64-product-v1"
        self.assertIsNone(_freeze_decision(detail))


class AdoptionUpgradeTests(TestCase):
    def test_v8_on_adoption_date_upgrades(self):
        detail = stamped_detail(PREVIOUS_MODEL_VERSION,
                                "v8-elo-speed2", "2026-11-04")
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value=EXTRAS):
            info = _lane_upgrade_info(detail)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "lane-upgrade-v9b-adoption")
        self.assertEqual(info["previousAbilityLane"], "v8-elo-speed2")

    def test_v8_on_other_dates_never_upgrades(self):
        detail = stamped_detail(PREVIOUS_MODEL_VERSION,
                                "v8-elo-speed2", "2026-11-05")
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value=EXTRAS):
            self.assertIsNone(_lane_upgrade_info(detail))

    def test_v8_adoption_date_without_extras_stays_frozen(self):
        detail = stamped_detail(PREVIOUS_MODEL_VERSION,
                                "v8-elo-speed2", "2026-11-04")
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value={}):
            self.assertIsNone(_lane_upgrade_info(detail))

    def test_v1_frozen_still_upgrades_with_plain_reason(self):
        detail = stamped_detail(PREVIOUS_MODEL_VERSION, "v1-prior",
                                "2026-11-04")
        with patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                   return_value=EXTRAS):
            info = _lane_upgrade_info(detail)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "lane-upgrade")
        self.assertEqual(info["previousAbilityLane"], "v1-prior")
