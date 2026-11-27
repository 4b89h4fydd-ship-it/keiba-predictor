"""Fresh-blend upgrade (2026-11-27): the re-issue of a frozen v9b
forecast whose market blend consumed stale win odds.

The 2026-11-27 races were all blended with odds observed around
00:22 JST — a median of ~14.9 hours before post — because first
publication happens overnight and the freeze never re-blended.
The mechanism added here re-issues such a race (full rebuild,
stamped kind "fresh-blend-upgrade") when the committed live-odds
feed carries a complete market that is fresher than the consumed
odds by at least the minimum advance, at least one active
runner's odds actually moved, and the post is still at least 30
minutes away. These tests pin the qualification matrix of
_fresh_blend_upgrade_info: the happy path, the feed-age and
advance guards, the completeness / roster-divergence guards,
the materiality requirement, and the repeat-application rule
(a second firing needs a further advance past the stamp).
"""
from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from rewrite.output.api_shape import MODEL_VERSION
from scripts import arvexq_rewrite_publish as publish
from scripts.arvexq_rewrite_publish import (
    V9B_LANE, _fresh_blend_upgrade_info)

JST = ZoneInfo("Asia/Tokyo")
RECEIPT = "a" * 64
RACE_ID = "nar-2026-11-27-園田-10"
DATE = "2026-11-27"
POST = "16:10"
PUBLISHED_AT = "2026-11-27T00:38:18+09:00"
NOW = datetime(2026, 11, 27, 15, 0, tzinfo=JST)  # 70 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
ODDS = {1: 2.4, 2: 3.1, 3: 5.5, 4: 9.0, 5: 21.0}
FEED_ODDS = {1: 2.1, 2: 3.4, 3: 5.5, 4: 9.0, 5: 21.0}
FEED_AT = "2026-11-27T05:52:00Z"  # 14:52 JST, 8 min before NOW


def stored_detail(*, blend_applied=True, odds=ODDS, lane=V9B_LANE,
                  fresh_stamp=None) -> dict:
    horses = []
    for number in (1, 2, 3, 4, 5):
        horse = {"horseNumber": number, "name": NAMES[number]}
        if odds is not None and number in odds:
            horse["winOdds"] = odds[number]
        horses.append(horse)
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": PUBLISHED_AT,
        "receiptSha256": RECEIPT,
        "abilityLane": lane,
        "blendApplied": blend_applied,
        "postProcessing": {
            "type": "temperature+market-blend", "temperature": 0.6692,
            "blendWeight": 0.5, "blendApplied": blend_applied},
        "overrideGuard": {"version": "override-guard-v1",
                          "applied": True},
    }
    if fresh_stamp is not None:
        marker["freshBlend"] = {"oddsUpdatedAt": fresh_stamp}
    roster = [{"horseNumber": h["horseNumber"], "name": h["name"]}
              for h in horses]
    return {
        "id": RACE_ID, "date": DATE, "scheduledStartTime": POST,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preparedMeta": {"rewritePublish": marker},
        "unifiedForecast": {"receiptSha256": RECEIPT, "roster": roster},
        "oddsUpdatedAt": "00:22:00",
        "horses": horses,
    }


def feed(*, odds=FEED_ODDS, at=FEED_AT, scratched=()) -> dict:
    return {
        "ok": True, "race_id": RACE_ID, "oddsSource": "NAR公式",
        "oddsUpdatedAt": at, "sourcePublishedAt": "",
        "odds": [
            {"horse_no": n, "win_odds": v,
             "scratched": n in scratched, "horse_status": ""}
            for n, v in odds.items()],
    }


def qualify(detail, feed_payload, now=NOW):
    with patch.object(publish, "_load_live_odds_feed",
                      return_value=feed_payload):
        return _fresh_blend_upgrade_info(detail, now)


class FreshBlendQualificationTests(TestCase):
    def test_qualifies_when_all_conditions_hold(self):
        info = qualify(stored_detail(), feed())
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "fresh-blend-upgrade")
        self.assertEqual(info["feedOdds"], FEED_ODDS)
        self.assertEqual(info["feedOddsUpdatedAt"], FEED_AT)
        self.assertEqual(info["previousOddsUpdatedAt"], "00:22:00")

    def test_unblended_forecast_never_qualifies(self):
        self.assertIsNone(qualify(stored_detail(blend_applied=False),
                                  feed()))

    def test_other_lanes_never_qualify(self):
        for lane in ("v8-elo-speed2", "v1-prior"):
            self.assertIsNone(
                qualify(stored_detail(lane=lane), feed()), lane)

    def test_missing_feed_never_qualifies(self):
        self.assertIsNone(qualify(stored_detail(), None))

    def test_stale_feed_never_qualifies(self):
        # Feed observed 30 minutes before NOW: past the 20-minute
        # freshness bound.
        self.assertIsNone(qualify(
            stored_detail(), feed(at="2026-11-27T05:30:00Z")))

    def test_feed_without_movement_never_qualifies(self):
        self.assertIsNone(qualify(stored_detail(), feed(odds=ODDS)))

    def test_incomplete_feed_never_qualifies(self):
        partial = {n: v for n, v in FEED_ODDS.items() if n != 5}
        self.assertIsNone(qualify(stored_detail(), feed(odds=partial)))

    def test_feed_scratching_an_active_runner_never_qualifies(self):
        self.assertIsNone(qualify(
            stored_detail(), feed(scratched=(2,))))

    def test_inside_the_t30_window_never_qualifies(self):
        late = datetime(2026, 11, 27, 15, 45, tzinfo=JST)
        self.assertIsNone(qualify(stored_detail(), feed(), now=late))

    def test_second_firing_needs_a_further_advance(self):
        # The standing forecast already consumed a feed stamped
        # 14:50 JST; a feed only 2 minutes newer must not fire.
        detail = stored_detail(fresh_stamp="2026-11-27T05:50:00Z")
        self.assertIsNone(qualify(detail, feed()))
        # A feed 7 minutes newer than the stamp does fire.
        info = qualify(detail, feed(at="2026-11-27T05:57:00Z"))
        self.assertIsNotNone(info)
        self.assertEqual(info["previousOddsUpdatedAt"],
                         "2026-11-27T05:50:00Z")
