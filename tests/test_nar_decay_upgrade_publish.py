"""NAR evidence-decay upgrade (2026-11-12): the one-time re-issue
of a NAR forecast frozen WITHOUT the F1 evidence decay.

The decay reached the production lane mid-day (PR #526), and the
user directed that the day's still-pre-post NAR races move to the
new method too ("from today's remaining races"). This branch is
the standing one-time upgrade pattern (blend / env-repair): a NAR
race frozen on the v9b lane whose sealed abilityModelVersion is
one of the undecayed labels is re-issued once from the current
payload. Exactly-once is structural — the re-issue stamps the
decayed label — and races past their post never reach the branch
(the build's post/result checks run first).

These tests pin the qualification matrix of
_nar_decay_upgrade_info, the structural exactly-once property,
the post-time lead guard, and — with the heavy collaborators
mocked at the publish module boundary — that a build-level
upgrade rebuilds through the decayed v8 layer, stamps the
revision chain, and keeps the frozen forecast when the rebuild
does not land on the decayed layer.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    NAR_DECAY_V9B_ABILITY_MODEL_VERSION,
    V8_ABILITY_MODEL_VERSION,
    V9B_ABILITY_MODEL_VERSION,
    V9B_LANE,
    _nar_decay_upgrade_info,
    build_publish_detail,
)
from tests.test_publish_mass_feature_archive import (
    EXTRAS,
    fabricated_race,
    v8_forecast,
)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
RACE_ID = "nar-2026-11-04-金沢-01"
DATE = "2026-11-04"
POST = "12:50"
PUBLISHED_AT = "2026-11-04T06:12:00+09:00"
NOW = datetime(2026, 11, 4, 10, 5, tzinfo=JST)  # 165 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}


def stored_detail(*, race_id=RACE_ID, lane=V9B_LANE,
                  ability_version=V9B_ABILITY_MODEL_VERSION,
                  post=POST) -> dict:
    horses = [{"horseNumber": n, "name": NAMES[n], "winOdds": 3.0}
              for n in (1, 2, 3, 4, 5)]
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": PUBLISHED_AT,
        "receiptSha256": RECEIPT,
        "abilityLane": lane,
        "temperature": 0.6692,
        "blendApplied": True,
        "postProcessing": {
            "type": "temperature+market-blend", "temperature": 0.6692,
            "blendWeight": 0.5, "blendApplied": True},
    }
    roster = [{"horseNumber": h["horseNumber"], "name": h["name"]}
              for h in horses]
    unified = {"receiptSha256": RECEIPT, "roster": roster}
    if ability_version is not None:
        unified["abilityModelVersion"] = ability_version
    return {
        "id": race_id, "date": DATE, "scheduledStartTime": post,
        "circuit": "地方", "venue": "金沢",
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "unifiedForecast": unified,
        "horses": horses,
    }


class NarDecayUpgradeQualificationTests(TestCase):
    def test_qualifies_when_all_conditions_hold(self):
        info = _nar_decay_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "nar-decay-upgrade")
        self.assertEqual(info["previousAbilityLane"], V9B_LANE)
        self.assertEqual(info["publishedAt"], PUBLISHED_AT)

    def test_v8_labelled_passthrough_also_qualifies(self):
        detail = stored_detail(ability_version=V8_ABILITY_MODEL_VERSION)
        self.assertIsNotNone(_nar_decay_upgrade_info(detail, NOW))

    def test_already_decayed_never_qualifies(self):
        # Structural exactly-once: the re-issue (and any later
        # first publication) stamps the decayed label.
        detail = stored_detail(
            ability_version=NAR_DECAY_V9B_ABILITY_MODEL_VERSION)
        self.assertIsNone(_nar_decay_upgrade_info(detail, NOW))

    def test_jra_never_qualifies(self):
        detail = stored_detail(race_id="jra-2026-11-04-東京-01")
        self.assertIsNone(_nar_decay_upgrade_info(detail, NOW))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            detail = stored_detail(lane=lane)
            self.assertIsNone(_nar_decay_upgrade_info(detail, NOW), lane)

    def test_unlabelled_product_never_qualifies(self):
        # A product without the v8/v9b ability label cannot be read
        # as an undecayed v8-layer publication — do not guess.
        detail = stored_detail(ability_version=None)
        self.assertIsNone(_nar_decay_upgrade_info(detail, NOW))
        detail = stored_detail(ability_version="something-else")
        self.assertIsNone(_nar_decay_upgrade_info(detail, NOW))

    def test_missing_marker_never_qualifies(self):
        detail = stored_detail()
        del detail["preparedMeta"]
        self.assertIsNone(_nar_decay_upgrade_info(detail, NOW))

    def test_post_lead_guard(self):
        # The lead guard was removed on 2026-11-12 (user
        # instruction): a race qualifies until its post, and a
        # race past its post never qualifies.
        detail = stored_detail()
        late = datetime(2026, 11, 4, 12, 40, tzinfo=JST)  # 10 min
        self.assertIsNotNone(_nar_decay_upgrade_info(detail, late))
        just_enough = datetime(2026, 11, 4, 12, 30, tzinfo=JST)
        self.assertIsNotNone(_nar_decay_upgrade_info(detail, just_enough))
        past_post = datetime(2026, 11, 4, 12, 51, tzinfo=JST)
        self.assertIsNone(_nar_decay_upgrade_info(detail, past_post))


def _build(detail, fake_v8):
    with patch("scripts.arvexq_rewrite_publish.normalize_race",
               return_value=fabricated_race()), \
            patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                  side_effect=fake_v8), \
            patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                  return_value=EXTRAS):
        return build_publish_detail(
            detail, {"race_id": RACE_ID, "id": RACE_ID}, NOW)


class NarDecayUpgradeBuildTests(TestCase):
    def test_build_reissues_with_decay_and_revision(self):
        calls = {}

        def fake_v8(race, extras, **kwargs):
            calls["evidence_decay_k"] = kwargs.get("evidence_decay_k")
            return v8_forecast()

        new, receipt = _build(stored_detail(), fake_v8)
        self.assertIsNotNone(new, receipt)
        self.assertEqual(calls["evidence_decay_k"], 2.0)
        self.assertEqual(new["unifiedForecast"]["abilityModelVersion"],
                         NAR_DECAY_V9B_ABILITY_MODEL_VERSION)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["evidenceDecay"]["scope"], "nar-only")
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "nar-decay-upgrade")
        self.assertEqual(revision["reason"], "nar-decay-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"], RECEIPT)
        self.assertIsNotNone(verified_unified(new))
        # And the rebuilt detail itself no longer qualifies.
        self.assertIsNone(_nar_decay_upgrade_info(new, NOW))

    def test_build_keeps_frozen_when_rebuild_misses_decay(self):
        def fake_v8(race, extras, **kwargs):
            forecast = v8_forecast()
            return type(forecast)(
                forecast.race_id, forecast.beta,
                forecast.probability_status, forecast.runners,
                "insufficient-scored-runners")

        with patch("scripts.arvexq_rewrite_publish.forecast_race",
                   return_value=v8_forecast()):
            new, reason = _build(stored_detail(), fake_v8)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)
        self.assertIn("nar-decay rebuild did not land", reason)


if __name__ == "__main__":
    import unittest
    unittest.main()
