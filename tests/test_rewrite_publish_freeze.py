"""Forecast freeze-at-first-publish for the rewrite publish lane.

A race this lane already published ready must stay byte-stable across
later publish cycles; only a roster change (scratch / added runner /
rename) re-issues it, stamped as a revision in the lane marker.
Frozen state is recognised from the stored detail itself: the
preparedMeta.rewritePublish marker, the ready status fields, and the
receipt roster inside the unified forecast. Unreadable frozen state
fails closed (skip, never overwrite).

The decision helper is pure, so these tests use synthetic details.
The freeze gate inside build_publish_detail runs before any forecast
computation, which lets the build-level tests use minimal details.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    _freeze_decision, build_publish_detail)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=JST)


def frozen_detail() -> dict:
    return {
        "id": "nar-2099-01-01-高知-12",
        "date": "2099-01-01",
        "scheduledStartTime": "20:50",
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": {
            "modelVersion": MODEL_VERSION,
            "publishedAt": "2026-11-01T08:00:00+09:00",
            "receiptSha256": RECEIPT,
            "abilityLane": "v8-elo-speed2"}},
        "unifiedForecast": {
            "receiptSha256": RECEIPT,
            "roster": [{"horseNumber": 1, "name": "アアア"},
                       {"horseNumber": 2, "name": "イイイ"},
                       {"horseNumber": 3, "name": "ウウウ"}]},
        "horses": [{"horseNumber": 1, "name": "アアア"},
                   {"horseNumber": 2, "name": "イイイ"},
                   {"horseNumber": 3, "name": "ウウウ"}],
    }


class FreezeDecisionTests(TestCase):
    def test_never_published_has_no_marker(self):
        detail = frozen_detail()
        del detail["preparedMeta"]
        self.assertIsNone(_freeze_decision(detail))

    def test_foreign_model_version_is_not_frozen(self):
        detail = frozen_detail()
        detail["preparedMeta"]["rewritePublish"]["modelVersion"] = (
            "arvexq-rewrite-v1-uncalibrated-prior")
        self.assertIsNone(_freeze_decision(detail))

    def test_not_ready_is_not_frozen(self):
        detail = frozen_detail()
        detail["predictionStatus"] = "disabled"
        self.assertIsNone(_freeze_decision(detail))

    def test_unchanged_roster_is_frozen(self):
        decision = _freeze_decision(frozen_detail())
        self.assertEqual(decision, ("frozen", RECEIPT))

    def test_scratch_triggers_reissue(self):
        detail = frozen_detail()
        detail["horses"][1]["status"] = "出走取消"
        kind, info = _freeze_decision(detail)
        self.assertEqual(kind, "reissue")
        self.assertEqual(info["removed"], [2])
        self.assertEqual(info["added"], [])
        self.assertEqual(info["receipt"], RECEIPT)

    def test_withdrawn_flag_triggers_reissue(self):
        detail = frozen_detail()
        detail["horses"][0]["scratched"] = True
        kind, info = _freeze_decision(detail)
        self.assertEqual(kind, "reissue")
        self.assertEqual(info["removed"], [1])

    def test_added_runner_triggers_reissue(self):
        detail = frozen_detail()
        detail["horses"].append({"horseNumber": 4, "name": "エエエ"})
        kind, info = _freeze_decision(detail)
        self.assertEqual(kind, "reissue")
        self.assertEqual(info["added"], [4])
        self.assertEqual(info["removed"], [])

    def test_renamed_runner_triggers_reissue(self):
        detail = frozen_detail()
        detail["horses"][2]["name"] = "ウウウ改"
        kind, info = _freeze_decision(detail)
        self.assertEqual(kind, "reissue")
        self.assertEqual(info["renamed"], [3])

    def test_missing_unified_forecast_fails_closed(self):
        detail = frozen_detail()
        del detail["unifiedForecast"]
        with self.assertRaises(ValueError):
            _freeze_decision(detail)

    def test_receipt_mismatch_fails_closed(self):
        detail = frozen_detail()
        detail["unifiedForecast"]["receiptSha256"] = "b" * 64
        with self.assertRaises(ValueError):
            _freeze_decision(detail)

    def test_missing_roster_fails_closed(self):
        detail = frozen_detail()
        del detail["unifiedForecast"]["roster"]
        with self.assertRaises(ValueError):
            _freeze_decision(detail)


class BuildFreezeGateTests(TestCase):
    def summary(self) -> dict:
        return {"race_id": "nar-2099-01-01-高知-12", "id": "nar-2099-01-01-高知-12"}

    def test_frozen_race_is_skipped_not_recomputed(self):
        new, reason = build_publish_detail(
            frozen_detail(), self.summary(),
            datetime(2099, 1, 1, 9, 0, tzinfo=JST))
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen:"), reason)

    def test_unreadable_frozen_state_fails_closed(self):
        detail = frozen_detail()
        detail["unifiedForecast"]["receiptSha256"] = "b" * 64
        new, reason = build_publish_detail(
            detail, self.summary(),
            datetime(2099, 1, 1, 9, 0, tzinfo=JST))
        self.assertIsNone(new)
        self.assertTrue(reason.startswith("frozen-state unreadable"), reason)

    def test_input_detail_is_not_mutated_by_the_gate(self):
        detail = frozen_detail()
        snapshot = deepcopy(detail)
        build_publish_detail(detail, self.summary(),
                             datetime(2099, 1, 1, 9, 0, tzinfo=JST))
        self.assertEqual(detail, snapshot)
