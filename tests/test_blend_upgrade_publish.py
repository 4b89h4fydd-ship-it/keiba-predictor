"""Blend upgrade (2026-11-04): the one-time re-issue of a v9b
forecast that was frozen WITHOUT its market blend.

On the v9b adoption night, 24 of the 59 races dated 2026-11-04
were published before their venues posted win odds, so the blend
was skipped and the races were frozen with temperature-only
probabilities. The standing mechanism added here re-issues such a
race exactly once when ALL of these hold: the stored lane is
v9b-cal-market with blendApplied false, the current payload has
win odds for every active runner, and the post is still at least
60 minutes away. The revision is stamped kind "blend-upgrade",
the first publication time is preserved, and once blended the
forecast is final — later odds movement never re-triggers it.

These tests pin the qualification matrix of _blend_upgrade_info,
the one-time property, the post-time guard, the fail-closed
behaviour of the build gate, and — with the heavy collaborators
mocked at the publish module boundary — that a build-level
upgrade emits exactly the shadow lane's v9b transform of the same
inputs (probabilities and marks) with the revision stamped.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.shadow_v9 import postprocess_forecast
from rewrite.data.normalize import Obs, RaceRecord, RunnerRecord, obs
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.safety.contracts import Segment
from scripts.arvexq_rewrite_publish import (
    V9B_LANE, _blend_upgrade_info, build_publish_detail)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
RACE_ID = "nar-2026-11-04-金沢-01"
DATE = "2026-11-04"
POST = "12:50"
PUBLISHED_AT = "2026-11-03T15:21:00+09:00"
NOW = datetime(2026, 11, 4, 10, 5, tzinfo=JST)  # 165 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
ODDS = {1: 2.4, 2: 3.1, 3: 5.5, 4: 9.0, 5: 21.0}
STRENGTHS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}


def stored_detail(*, blend_applied=False, odds=ODDS, lane=V9B_LANE,
                  post=POST, revision=None, blend_flag=True,
                  scratched=()) -> dict:
    horses = []
    for number in (1, 2, 3, 4, 5):
        horse = {"horseNumber": number, "name": NAMES[number]}
        if odds is not None and number in odds:
            horse["winOdds"] = odds[number]
        if number in scratched:
            horse["status"] = "出走取消"
        horses.append(horse)
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": PUBLISHED_AT,
        "receiptSha256": RECEIPT,
        "abilityLane": lane,
        "temperature": 0.6692,
    }
    if blend_flag:
        marker["blendApplied"] = blend_applied
        marker["postProcessing"] = {
            "type": "temperature+market-blend", "temperature": 0.6692,
            "blendWeight": 0.5, "blendApplied": blend_applied}
    if revision is not None:
        marker["revision"] = revision
    roster = [{"horseNumber": h["horseNumber"], "name": h["name"]}
              for h in horses if h["horseNumber"] not in scratched]
    return {
        "id": RACE_ID, "date": DATE, "scheduledStartTime": post,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "unifiedForecast": {"receiptSha256": RECEIPT, "roster": roster},
        "horses": horses,
    }


class BlendUpgradeQualificationTests(TestCase):
    def test_qualifies_when_all_conditions_hold(self):
        info = _blend_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "blend-upgrade")
        self.assertEqual(info["previousAbilityLane"], V9B_LANE)
        self.assertEqual(info["publishedAt"], PUBLISHED_AT)

    def test_blend_already_applied_never_qualifies(self):
        detail = stored_detail(blend_applied=True)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            detail = stored_detail(lane=lane)
            self.assertIsNone(_blend_upgrade_info(detail, NOW), lane)

    def test_missing_marker_never_qualifies(self):
        detail = stored_detail()
        del detail["preparedMeta"]
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_unrecorded_blend_flag_never_qualifies(self):
        # A v9b publication always stamps the blend flag; its
        # absence means the stored state cannot be read as the
        # mechanism requires — do not guess.
        detail = stored_detail(blend_flag=False)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_blend_flag_read_from_post_processing_fallback(self):
        detail = stored_detail()
        marker = detail["preparedMeta"]["rewritePublish"]
        del marker["blendApplied"]
        info = _blend_upgrade_info(detail, NOW)
        self.assertIsNotNone(info)

    def test_incomplete_odds_never_qualify(self):
        odds = dict(ODDS)
        del odds[5]
        detail = stored_detail(odds=odds)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_no_odds_at_all_never_qualifies(self):
        detail = stored_detail(odds=None)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_odds_of_exactly_one_block(self):
        odds = dict(ODDS)
        odds[3] = 1.0
        detail = stored_detail(odds=odds)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_scratched_runner_without_odds_does_not_block(self):
        odds = dict(ODDS)
        del odds[5]
        detail = stored_detail(odds=odds, scratched=(5,))
        self.assertIsNotNone(_blend_upgrade_info(detail, NOW))


class BlendUpgradePostGuardTests(TestCase):
    def test_inside_sixty_minutes_never_qualifies(self):
        now = datetime(2026, 11, 4, 11, 51, tzinfo=JST)  # 59 min
        self.assertIsNone(_blend_upgrade_info(stored_detail(), now))

    def test_exactly_sixty_minutes_qualifies(self):
        now = datetime(2026, 11, 4, 11, 50, tzinfo=JST)  # 60 min
        self.assertIsNotNone(_blend_upgrade_info(stored_detail(), now))

    def test_after_post_never_qualifies(self):
        now = datetime(2026, 11, 4, 13, 0, tzinfo=JST)
        self.assertIsNone(_blend_upgrade_info(stored_detail(), now))


class BlendUpgradeOneTimeTests(TestCase):
    def test_post_upgrade_state_never_requalifies(self):
        # The state a successful upgrade leaves behind: the blend
        # flag is true and the revision carries the upgrade kind.
        # Neither later odds movement nor any later cycle may
        # re-trigger it.
        revision = {"kind": "blend-upgrade", "reason": "blend-upgrade",
                    "revisedAt": "2026-11-04T10:05:00+09:00",
                    "revisionCount": 1,
                    "previousReceiptSha256": RECEIPT}
        detail = stored_detail(blend_applied=True, revision=revision)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))

    def test_existing_upgrade_revision_blocks_even_with_flag_lost(self):
        revision = {"kind": "blend-upgrade", "reason": "blend-upgrade",
                    "revisedAt": "2026-11-04T10:05:00+09:00",
                    "revisionCount": 1,
                    "previousReceiptSha256": RECEIPT}
        detail = stored_detail(blend_applied=False, revision=revision)
        self.assertIsNone(_blend_upgrade_info(detail, NOW))


def fabricated_race(odds=ODDS) -> RaceRecord:
    missing = Obs(None, "test", "not_captured")
    runners = []
    for number in (1, 2, 3, 4, 5):
        runners.append(RunnerRecord(
            number=number, horse_id=missing,
            name=obs(NAMES[number], "test"), frame_number=missing,
            age=missing, sex=missing, jockey=missing, trainer=missing,
            carried_weight=missing, body_weight=missing,
            body_weight_change=missing,
            win_odds=obs(odds.get(number), "test")
            if odds else missing,
            scratched=False, past_runs=()))
    return RaceRecord(
        race_id=RACE_ID, date=DATE, circuit=obs("地方", "test"),
        track="金沢", race_number=obs(1, "test"), title=missing,
        start_time=obs(POST, "test"), distance=obs(1500, "test"),
        surface=obs("ダート", "test"), weather=missing,
        condition=missing, updated_at=missing, segment=Segment.NAR,
        source="test", runners=tuple(runners))


def v8_forecast() -> RaceForecast:
    runners = [RunnerForecast(
        number=n, name=NAMES[n], ability_score=0.5, strength=s,
        pace_adjustment=1.0, pace_reasons=(), p_win=None, p_top2=None,
        p_top3=None, mark="", status="scored")
        for n, s in STRENGTHS.items()]
    return RaceForecast(RACE_ID, 3.0, "uncalibrated-prior",
                        tuple(runners), "ok")


EXTRAS = {RACE_ID: {"segment": "nar",
                    "extras": {str(n): {"elo": 1500.0} for n in NAMES}}}


def summary() -> dict:
    return {"race_id": RACE_ID, "id": RACE_ID}


class BlendUpgradeBuildTests(TestCase):
    def test_unqualified_frozen_race_stays_frozen(self):
        odds = dict(ODDS)
        del odds[5]
        new, reason = build_publish_detail(
            stored_detail(odds=odds), summary(), NOW)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)

    def test_unreadable_frozen_state_fails_closed(self):
        detail = stored_detail()
        detail["unifiedForecast"]["receiptSha256"] = "b" * 64
        new, reason = build_publish_detail(detail, summary(), NOW)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen-state unreadable"),
                        reason)

    def test_upgrade_rebuild_that_misses_the_blend_keeps_frozen(self):
        # The stored card shows complete odds (qualification
        # holds) but the rebuilt race's own odds are incomplete,
        # so the transform falls back to temperature-only:
        # re-issuing would rewrite a forecast on sale without the
        # one change that justifies it. The build must refuse.
        partial = dict(ODDS)
        del partial[5]
        with patch("scripts.arvexq_rewrite_publish.normalize_race",
                   return_value=fabricated_race(partial)), \
                patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                      return_value=v8_forecast()), \
                patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                      return_value=EXTRAS):
            new, reason = build_publish_detail(
                stored_detail(), summary(), NOW)
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)
        self.assertIn("blend upgrade did not land", reason)

    def test_successful_upgrade_stamps_revision_and_matches_shadow(self):
        base = v8_forecast()
        expected, info = postprocess_forecast(base, arm="v9b",
                                              win_odds=ODDS)
        self.assertTrue(info["blendApplied"])
        with patch("scripts.arvexq_rewrite_publish.normalize_race",
                   return_value=fabricated_race()), \
                patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                      return_value=base), \
                patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                      return_value=EXTRAS):
            new, receipt = build_publish_detail(
                stored_detail(), summary(), NOW)
        self.assertIsNotNone(new, receipt)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["abilityLane"], V9B_LANE)
        self.assertTrue(marker["blendApplied"])
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "blend-upgrade")
        self.assertEqual(revision["reason"], "blend-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"], RECEIPT)
        # Probabilities and marks equal the shadow lane's v9b
        # transform of the same v8 forecast and the same odds.
        expected_win = {r.number: round(r.p_win, 6)
                        for r in expected.runners}
        actual_win = new["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertEqual(
            {int(k): v for k, v in actual_win.items()}, expected_win)
        expected_marks = {r.number: r.mark for r in expected.runners}
        actual_marks = {m["horseNumber"]: m["mark"]
                        for m in new["predictionMarks"]}
        self.assertEqual(actual_marks, expected_marks)
        # The upgraded state can never qualify again.
        upgraded_marker_detail = stored_detail(
            blend_applied=True, revision=revision)
        self.assertIsNone(
            _blend_upgrade_info(upgraded_marker_detail, NOW))
