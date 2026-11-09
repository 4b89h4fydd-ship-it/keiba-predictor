"""Env-repair re-issue (2026-11-09): the one-time recompute of a
v9b forecast whose probabilities were computed while the NAR
surface builders served "".

Until main 2e01ec9e (committed 2026-11-09 10:21 JST) the NAR
summary/detail builders hardcoded the race surface to "", so the
surface suitability feature was dead in every forecast computed
from those payloads. By user instruction (2026-11-09) a frozen
v9b forecast dated 2026-11-09 (NAR) whose probabilities were last
computed before the fix is re-issued once, stamped kind
"env-repair-upgrade", recomputed from the current payload.

These tests pin the qualification matrix of
_env_repair_upgrade_info: the dated/NAR scope, the probability
computation-time rule (recomputing revisions set it, surgical
ones do not), the exactly-once property, the live-surface
requirement and the post-time guard.
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    V9B_LANE, _env_repair_upgrade_info)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
RACE_ID = "nar-2026-11-09-川崎-05"
DATE = "2026-11-09"
POST = "17:00"
FIRST_PUBLISHED_AT = "2026-11-08T21:54:25+09:00"
NOW = datetime(2026, 11, 9, 15, 0, tzinfo=JST)  # 120 min before post


def stored_detail(*, race_id=RACE_ID, date=DATE, post=POST,
                  lane=V9B_LANE, surface="ダート", revision=None,
                  first_published_at=FIRST_PUBLISHED_AT,
                  published_at=None) -> dict:
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": published_at or first_published_at,
        "firstPublishedAt": first_published_at,
        "receiptSha256": RECEIPT,
        "abilityLane": lane,
        "temperature": 0.6692,
        "blendApplied": True,
        "postProcessing": {
            "type": "temperature+market-blend", "temperature": 0.6692,
            "blendWeight": 0.5, "blendApplied": True},
    }
    if revision is not None:
        marker["revision"] = revision
    return {
        "id": race_id, "date": date, "scheduledStartTime": post,
        "surface": surface,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "horses": [{"horseNumber": 1, "name": "アアア",
                    "winOdds": 2.4}],
    }


def revision(kind, revised_at, *, with_kind=True):
    rev = {"reason": kind, "revisedAt": revised_at,
           "revisionCount": 1, "previousReceiptSha256": "b" * 64}
    if with_kind:
        rev["kind"] = kind
    return rev


class EnvRepairQualificationTests(TestCase):
    def test_qualifies_when_probabilities_predate_the_fix(self):
        info = _env_repair_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "env-repair-upgrade")
        self.assertEqual(info["surface"], "ダート")
        self.assertEqual(info["probabilityComputedAt"],
                         FIRST_PUBLISHED_AT)
        self.assertEqual(info["firstPublishedAt"], FIRST_PUBLISHED_AT)

    def test_surgical_revision_on_top_still_qualifies(self):
        # place-ev / ticket-r24 revisions keep the stored
        # probabilities, so a post-fix stamp on top does not move
        # the computation time past the fix.
        for kind in ("place-ev-upgrade", "ticket-r24-upgrade"):
            detail = stored_detail(revision=revision(
                kind, "2026-11-09T14:01:20+09:00"))
            info = _env_repair_upgrade_info(detail, NOW)
            self.assertIsNotNone(info, kind)
            self.assertEqual(info["probabilityComputedAt"],
                             FIRST_PUBLISHED_AT)

    def test_blend_revision_before_fix_sets_computation_time(self):
        detail = stored_detail(revision=revision(
            "blend-upgrade", "2026-11-09T02:16:06+09:00"))
        info = _env_repair_upgrade_info(detail, NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["probabilityComputedAt"],
                         "2026-11-09T02:16:06+09:00")

    def test_recomputed_after_fix_does_not_qualify(self):
        for kind in ("blend-upgrade", "lane-upgrade"):
            detail = stored_detail(revision=revision(
                kind, "2026-11-09T11:05:00+09:00"))
            self.assertIsNone(_env_repair_upgrade_info(detail, NOW),
                              kind)
        # Roster-change revisions carry no "kind", only "reason".
        detail = stored_detail(revision=revision(
            "roster-change", "2026-11-09T14:02:11+09:00",
            with_kind=False))
        self.assertIsNone(_env_repair_upgrade_info(detail, NOW))

    def test_exactly_once(self):
        detail = stored_detail(revision=revision(
            "env-repair-upgrade", "2026-11-09T14:40:00+09:00"))
        self.assertIsNone(_env_repair_upgrade_info(detail, NOW))

    def test_scope_is_dated_and_nar_only(self):
        self.assertIsNone(_env_repair_upgrade_info(
            stored_detail(date="2026-11-10"), NOW))
        self.assertIsNone(_env_repair_upgrade_info(
            stored_detail(race_id="jra-2026-11-09-東京-05"), NOW))

    def test_requires_the_live_surface(self):
        self.assertIsNone(_env_repair_upgrade_info(
            stored_detail(surface=""), NOW))
        self.assertIsNone(_env_repair_upgrade_info(
            stored_detail(surface=None), NOW))

    def test_requires_v9b_lane_and_a_readable_marker(self):
        self.assertIsNone(_env_repair_upgrade_info(
            stored_detail(lane="v8-elo-speed2"), NOW))
        detail = stored_detail()
        detail["preparedMeta"] = {}
        self.assertIsNone(_env_repair_upgrade_info(detail, NOW))

    def test_post_guard(self):
        # 20 minutes before post: inside the final half hour.
        inside = datetime(2026, 11, 9, 16, 40, tzinfo=JST)
        self.assertIsNone(_env_repair_upgrade_info(
            stored_detail(), inside))
        # Exactly 30 minutes before post still qualifies.
        edge = datetime(2026, 11, 9, 16, 30, tzinfo=JST)
        self.assertIsNotNone(_env_repair_upgrade_info(
            stored_detail(), edge))
