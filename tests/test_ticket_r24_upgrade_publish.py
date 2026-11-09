"""Ticket-R24 upgrade (2026-11-08): the one-time re-issue of a
forecast frozen with the formation-B trifecta recommendation.

By user order the production trifecta recommendation switched
from formation B (win leg = mark ranks 1-3, 36 points) to R24
(win leg = mark ranks 1-2, 24 points). New publications build
R24 directly; a race already frozen with the B-form trifecta is
re-issued exactly once, stamped kind "ticket-r24-upgrade", with
ONLY the trifecta recommendation narrowed to the R24 subset of
the stored combinations. The forecast, marks, probabilities and
every other ticket kind stay byte-for-byte the stored ones.

These tests pin the qualification matrix of
_ticket_r24_upgrade_info, the surgical property of
_apply_ticket_r24_upgrade (nothing but the trifecta blocks and
the marker move), the exactly-once property, the fail-closed
behaviour, and the build-level gate in build_publish_detail.
"""
from __future__ import annotations

import copy
from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from rewrite.analysis.tickets import (
    formation_b_selections, formation_r24_selections)
from rewrite.output.api_shape import MODEL_VERSION
from scripts.arvexq_rewrite_publish import (
    V9B_LANE, _apply_ticket_r24_upgrade, _canonical_receipt,
    _ticket_r24_upgrade_info, build_publish_detail)

JST = ZoneInfo("Asia/Tokyo")
RACE_ID = "jra-2026-11-08-京都-01"
DATE = "2026-11-08"
POST = "15:00"
PUBLISHED_AT = "2026-11-07T12:05:00+09:00"
NOW = datetime(2026, 11, 8, 10, 0, tzinfo=JST)  # 300 min before post
NAMES = {1: "アアア", 2: "イイイ", 3: "ウウウ", 4: "エエエ", 5: "オオオ"}
MARKS = {2: "◎", 1: "○", 3: "▲", 5: "△", 4: "☆"}
MARK_ORDER = [2, 1, 3, 5, 4]


def stored_detail(*, lane=V9B_LANE, revision=None, combos=None,
                  post=POST) -> dict:
    horses = [{"horseNumber": n, "name": NAMES[n]} for n in (1, 2, 3, 4, 5)]
    b_combos = [list(c) for c in formation_b_selections(MARK_ORDER)]
    grouped = [
        {"kind": "ワイド", "combos": [[2, 1], [2, 3]], "points": 2,
         "reason": "同一モデル"},
        {"kind": "3連単", "combos": combos if combos is not None else b_combos,
         "points": len(combos) if combos is not None else len(b_combos),
         "reason": "同一モデル"},
    ]
    unified = {
        "version": "arvexq-unified-live-v1",
        "raceId": RACE_ID,
        "modelVersion": MODEL_VERSION,
        "roster": [{"horseNumber": n, "name": NAMES[n]}
                   for n in (1, 2, 3, 4, 5)],
        "marks": [{"horseNumber": n, "markSymbol": MARKS[n],
                   "winProbability": 0.2} for n in MARK_ORDER],
        "diagnosis": [{"horseNumber": n, "winProbability": 0.2,
                       "top3Probability": 0.5} for n in (1, 2, 3, 4, 5)],
        "ticketPlan": {
            "status": "参考候補",
            "items": [
                {"kind": "馬単", "combo": [2, 1], "probability": 0.09},
                {"kind": "3連単", "combo": [2, 1, 3], "probability": 0.03},
                {"kind": "3連単", "combo": [3, 2, 1], "probability": 0.02},
            ],
            "winExpectedValues": [],
            "suppressed": {},
        },
    }
    unified["receiptSha256"] = _canonical_receipt(unified)
    marker = {
        "modelVersion": MODEL_VERSION,
        "publishedAt": PUBLISHED_AT,
        "firstPublishedAt": PUBLISHED_AT,
        "receiptSha256": unified["receiptSha256"],
        "abilityLane": lane,
        "blendApplied": True,
    }
    if revision is not None:
        marker["revision"] = revision
    return {
        "id": RACE_ID, "date": DATE, "scheduledStartTime": post,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "horses": horses,
        "predictionMarks": [{"horseNumber": n, "mark": MARKS[n]}
                            for n in MARK_ORDER],
        "unifiedForecast": unified,
        "recommendedBets": grouped,
        "prediction": {"predictionMarks": [{"horseNumber": n, "mark": MARKS[n]}
                                           for n in MARK_ORDER]},
        "preparedMeta": {"rewritePublish": marker},
    }


class TicketR24QualificationTests(TestCase):
    def test_qualifies_on_frozen_b_form(self):
        info = _ticket_r24_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "ticket-r24-upgrade")
        self.assertEqual(info["markOrder"], MARK_ORDER)
        self.assertEqual(info["previousAbilityLane"], V9B_LANE)

    def test_already_r24_never_qualifies(self):
        r24 = [list(c) for c in formation_r24_selections(MARK_ORDER)]
        self.assertIsNone(
            _ticket_r24_upgrade_info(stored_detail(combos=r24), NOW))

    def test_non_b_construction_never_qualifies(self):
        bogus = [[1, 2, 3], [4, 5, 1]]
        self.assertIsNone(
            _ticket_r24_upgrade_info(stored_detail(combos=bogus), NOW))

    def test_existing_upgrade_revision_blocks(self):
        revision = {"kind": "ticket-r24-upgrade",
                    "reason": "ticket-r24-upgrade",
                    "revisedAt": "2026-11-08T02:05:00+09:00",
                    "revisionCount": 1}
        self.assertIsNone(_ticket_r24_upgrade_info(
            stored_detail(revision=revision), NOW))

    def test_inside_sixty_minutes_never_qualifies(self):
        now = datetime(2026, 11, 8, 14, 1, tzinfo=JST)  # 59 min
        self.assertIsNone(_ticket_r24_upgrade_info(stored_detail(), now))

    def test_exactly_sixty_minutes_qualifies(self):
        now = datetime(2026, 11, 8, 14, 0, tzinfo=JST)  # 60 min
        self.assertIsNotNone(_ticket_r24_upgrade_info(stored_detail(), now))

    def test_missing_ticket_plan_never_qualifies(self):
        detail = stored_detail()
        del detail["unifiedForecast"]["ticketPlan"]
        self.assertIsNone(_ticket_r24_upgrade_info(detail, NOW))

    def test_mark_blocks_disagreeing_never_qualify(self):
        detail = stored_detail()
        detail["unifiedForecast"]["marks"][0]["markSymbol"] = "○"
        detail["unifiedForecast"]["marks"][1]["markSymbol"] = "◎"
        self.assertIsNone(_ticket_r24_upgrade_info(detail, NOW))


class TicketR24ApplyTests(TestCase):
    def _upgrade(self, detail=None):
        detail = detail if detail is not None else stored_detail()
        info = _ticket_r24_upgrade_info(detail, NOW)
        self.assertIsNotNone(info)
        info["receipt"] = detail["unifiedForecast"]["receiptSha256"]
        return detail, _apply_ticket_r24_upgrade(
            detail, info, NOW.isoformat(timespec="seconds"))

    def test_trifecta_narrowed_to_canonical_r24(self):
        _old, upgraded = self._upgrade()
        self.assertIsNotNone(upgraded)
        new, _receipt = upgraded
        trifecta = next(b for b in new["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 24)
        self.assertEqual({tuple(c) for c in trifecta["combos"]},
                         set(formation_r24_selections(MARK_ORDER)))
        for combo in trifecta["combos"]:
            self.assertIn(combo[0], MARK_ORDER[:2])
        # The prediction mirror carries the same narrowed list.
        self.assertEqual(new["prediction"]["recommendedBets"],
                         new["recommendedBets"])
        # The unified ticket plan's 3連単 items are filtered too;
        # the ▲-headed item is gone, the ◎-headed one stays.
        items = new["unifiedForecast"]["ticketPlan"]["items"]
        self.assertEqual([i["combo"] for i in items
                          if i["kind"] == "3連単"], [[2, 1, 3]])

    def test_everything_else_byte_identical(self):
        old, (new, receipt) = self._upgrade()
        self.assertEqual(new["predictionMarks"], old["predictionMarks"])
        self.assertEqual(new["unifiedForecast"]["marks"],
                         old["unifiedForecast"]["marks"])
        self.assertEqual(new["unifiedForecast"]["diagnosis"],
                         old["unifiedForecast"]["diagnosis"])
        self.assertEqual(new["unifiedForecast"]["ticketPlan"]
                         ["winExpectedValues"],
                         old["unifiedForecast"]["ticketPlan"]
                         ["winExpectedValues"])
        for kind in ("ワイド",):
            self.assertEqual(
                next(b for b in new["recommendedBets"] if b["kind"] == kind),
                next(b for b in old["recommendedBets"] if b["kind"] == kind))
        self.assertEqual(new["horses"], old["horses"])
        # The receipt is re-sealed over the modified unified product.
        self.assertEqual(receipt,
                         _canonical_receipt(new["unifiedForecast"]))
        self.assertNotEqual(receipt, old["unifiedForecast"]["receiptSha256"])

    def test_revision_stamped_and_first_publication_preserved(self):
        old, (new, _receipt) = self._upgrade()
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "ticket-r24-upgrade")
        self.assertEqual(revision["reason"], "ticket-r24-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"],
                         old["unifiedForecast"]["receiptSha256"])
        self.assertEqual(revision["abilityLane"], V9B_LANE)

    def test_exactly_once(self):
        _old, (new, _receipt) = self._upgrade()
        self.assertIsNone(_ticket_r24_upgrade_info(new, NOW))

    def test_apply_fails_closed_on_unexpected_combos(self):
        detail = stored_detail(combos=[[1, 2, 3], [2, 3, 1], [3, 1, 2],
                                       [1, 3, 2], [2, 1, 3], [3, 2, 1]])
        info = {"publishedAt": PUBLISHED_AT,
                "firstPublishedAt": PUBLISHED_AT,
                "previousAbilityLane": V9B_LANE,
                "reason": "ticket-r24-upgrade",
                "markOrder": MARK_ORDER, "receipt": "x" * 64}
        self.assertIsNone(_apply_ticket_r24_upgrade(
            detail, info, NOW.isoformat(timespec="seconds")))


class TicketR24BuildGateTests(TestCase):
    def test_build_reissues_frozen_b_form_with_r24(self):
        detail = stored_detail()
        summary = {"race_id": RACE_ID, "id": RACE_ID}
        new, receipt = build_publish_detail(
            copy.deepcopy(detail), summary, NOW)
        self.assertIsNotNone(new)
        trifecta = next(b for b in new["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 24)
        revision = new["preparedMeta"]["rewritePublish"]["revision"]
        self.assertEqual(revision["kind"], "ticket-r24-upgrade")
        self.assertEqual(receipt, new["unifiedForecast"]["receiptSha256"])
        # Marks and probabilities are the stored ones.
        self.assertEqual(new["predictionMarks"], detail["predictionMarks"])
        self.assertEqual(new["unifiedForecast"]["diagnosis"],
                         detail["unifiedForecast"]["diagnosis"])

    def test_build_leaves_r24_frozen_detail_alone(self):
        r24 = [list(c) for c in formation_r24_selections(MARK_ORDER)]
        detail = stored_detail(combos=r24)
        # Keep the receipt chain consistent after the combo swap.
        detail["unifiedForecast"]["receiptSha256"] = _canonical_receipt(
            detail["unifiedForecast"])
        detail["preparedMeta"]["rewritePublish"]["receiptSha256"] = (
            detail["unifiedForecast"]["receiptSha256"])
        new, reason = build_publish_detail(
            copy.deepcopy(detail), {"race_id": RACE_ID, "id": RACE_ID}, NOW)
        self.assertIsNone(new)
        self.assertTrue(str(reason).startswith("frozen:"), reason)
