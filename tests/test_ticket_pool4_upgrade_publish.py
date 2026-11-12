"""The one-time ticket-pool4 upgrade and the P4A2 fresh build.

Pool4-axis2 (P4A2) replaced R24 as the NAR trifecta formation by
user order 2026-11-12 (offline sweep: set A ROI 0.662 vs R24
0.486, set AB 0.800 vs 0.629; probability cut left out — its
standalone effect is unestablished). JRA keeps R24 and is never
touched by any of this.

Fresh NAR publications are generated directly with P4A2 (and the
lane marker records ticketFormation); NAR publications already
frozen with the R24 trifecta are narrowed by the publish lane's
surgical one-time ticket-pool4-upgrade, exactly parallel to the
2026-11-08 ticket-r24-upgrade: the leg pool of the stored combos
shrinks to mark ranks 1-4 (12 points), the receipt is re-sealed,
firstPublishedAt is preserved, and the pass refuses anything
that is not exactly the R24 configuration.
"""
import copy
import dataclasses
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from arvexq.prediction.unified_product import verified as verified_unified
from rewrite.output.api_shape import MODEL_VERSION
from rewrite.analysis.tickets import (
    formation_pool4_axis2_selections,
    formation_r24_selections,
)
from scripts.arvexq_rewrite_publish import (
    NAR_TRIFECTA_FORMATION,
    _apply_ticket_pool4_upgrade,
    _canonical_receipt,
    _ticket_pool4_upgrade_info,
    build_publish_detail,
)
from tests.test_nar_evidence_decay_production import (
    JRA_EXTRAS,
    JRA_RACE_ID,
)
from rewrite.data.normalize import obs
from rewrite.safety.contracts import Segment
from tests.test_publish_mass_feature_archive import (
    EXTRAS as NAR_EXTRAS,
    NOW as FRESH_NOW,
    fabricated_race,
    fresh_detail,
    v8_forecast,
)

JST = ZoneInfo("Asia/Tokyo")
RACE_ID = "nar-2026-11-12-川崎-11"
JRA_FROZEN_ID = "jra-2026-11-12-東京-11"
DATE = "2026-11-12"
POST = "20:10"
PUBLISHED_AT = "2026-11-12T09:38:29+09:00"
NOW = datetime(2026, 11, 12, 17, 0, tzinfo=JST)  # 190 min before post
MARK_ORDER = [2, 1, 3, 5, 4]  # ◎ ○ ▲ △ ☆
MARK_SYMBOLS = {2: "◎", 1: "○", 3: "▲", 5: "△", 4: "☆"}
V9B_LANE = "v9b-cal-market"


def _trifecta_entry(combos):
    return {"kind": "3連単", "label": "3連単",
            "combos": [list(c) for c in combos],
            "points": len(combos)}


def stored_detail(combos=None, revision=None, race_id=RACE_ID):
    """A detail frozen before the switch: R24 trifecta, the full
    five marks, unified receipt consistent with the content.
    Mirrors tests.test_ticket_r24_upgrade_publish.stored_detail."""
    combos = (formation_r24_selections(MARK_ORDER)
              if combos is None else combos)
    names = {n: f"H{n}" for n in range(1, 6)}
    plan_items = [
        # Trifecta items: clean ones survive the narrowing, any
        # item carrying ☆ (mark rank 5) in any leg is dropped.
        {"kind": "3連単", "combo": [2, 1, 3], "probability": 0.05},
        {"kind": "3連単", "combo": [2, 1, 4], "probability": 0.03},
        {"kind": "3連単", "combo": [2, 4, 1], "probability": 0.02},
        {"kind": "3連単", "combo": [1, 2, 5], "probability": 0.04},
        {"kind": "馬連", "combo": [2, 1], "probability": 0.2},
    ]
    unified = {
        "version": "arvexq-unified-live-v1",
        "raceId": race_id,
        "modelVersion": MODEL_VERSION,
        "roster": [{"horseNumber": n, "name": names[n]}
                   for n in range(1, 6)],
        "marks": [{"horseNumber": n, "markSymbol": MARK_SYMBOLS[n],
                   "winProbability": 0.2} for n in MARK_ORDER],
        "diagnosis": [{"horseNumber": n, "winProbability": 0.2,
                       "top3Probability": 0.5} for n in range(1, 6)],
        "ticketPlan": {"status": "参考候補", "items": plan_items,
                       "winExpectedValues": [],
                       "suppressed": {}},
    }
    unified["receiptSha256"] = _canonical_receipt(unified)
    marker = {"modelVersion": MODEL_VERSION,
              "publishedAt": PUBLISHED_AT,
              "firstPublishedAt": PUBLISHED_AT,
              "receiptSha256": unified["receiptSha256"],
              "abilityLane": V9B_LANE,
              "blendApplied": True}
    if revision is not None:
        marker["revision"] = revision
    detail = {
        "id": race_id, "date": DATE, "scheduledStartTime": POST,
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "horses": [{"horseNumber": n, "name": names[n]}
                   for n in range(1, 6)],
        "predictionMarks": [{"horseNumber": n, "mark": MARK_SYMBOLS[n]}
                            for n in MARK_ORDER],
        "recommendedBets": [
            _trifecta_entry(combos),
            {"kind": "ワイド", "label": "ワイド",
             "combos": [[2, 1]], "points": 1},
        ],
        "prediction": {"predictionMarks": [
            {"horseNumber": n, "mark": MARK_SYMBOLS[n]}
            for n in MARK_ORDER]},
        "unifiedForecast": unified,
        "preparedMeta": {"rewritePublish": marker},
    }
    detail["prediction"]["recommendedBets"] = copy.deepcopy(
        detail["recommendedBets"])
    return detail


class TicketPool4QualificationTests(TestCase):
    def test_nar_r24_publication_qualifies(self):
        info = _ticket_pool4_upgrade_info(stored_detail(), NOW)
        self.assertIsNotNone(info)
        self.assertEqual(info["reason"], "ticket-pool4-upgrade")
        self.assertEqual(info["markOrder"], MARK_ORDER)

    def test_jra_publication_never_qualifies(self):
        detail = stored_detail(race_id=JRA_FROZEN_ID)
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))

    def test_b_form_publication_never_qualifies(self):
        from rewrite.analysis.tickets import formation_b_selections
        detail = stored_detail(combos=formation_b_selections(MARK_ORDER))
        detail["unifiedForecast"]["receiptSha256"] = _canonical_receipt(
            detail["unifiedForecast"])
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))

    def test_already_p4a2_never_qualifies(self):
        detail = stored_detail(
            combos=formation_pool4_axis2_selections(MARK_ORDER))
        detail["unifiedForecast"]["receiptSha256"] = _canonical_receipt(
            detail["unifiedForecast"])
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))

    def test_ticket_formation_marker_blocks(self):
        detail = stored_detail()
        detail["preparedMeta"]["rewritePublish"]["ticketFormation"] = {
            "formation": "P4A2", "scope": "nar-only"}
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))

    def test_existing_pool4_revision_blocks(self):
        revision = {"kind": "ticket-pool4-upgrade",
                    "reason": "ticket-pool4-upgrade",
                    "revisedAt": "2026-11-12T16:05:00+09:00",
                    "revisionCount": 1}
        self.assertIsNone(_ticket_pool4_upgrade_info(
            stored_detail(revision=revision), NOW))

    def test_inside_sixty_minutes_never_qualifies(self):
        now = datetime(2026, 11, 12, 19, 11, tzinfo=JST)  # 59 min
        self.assertIsNone(_ticket_pool4_upgrade_info(stored_detail(), now))

    def test_exactly_sixty_minutes_qualifies(self):
        now = datetime(2026, 11, 12, 19, 10, tzinfo=JST)  # 60 min
        self.assertIsNotNone(_ticket_pool4_upgrade_info(
            stored_detail(), now))

    def test_four_mark_publication_never_qualifies(self):
        # With four marks R24 and P4A2 coincide — nothing to do,
        # and the stored receipt chain stays untouched.
        detail = stored_detail(
            combos=formation_r24_selections(MARK_ORDER[:4]))
        marks = detail["unifiedForecast"]["marks"][:4]
        detail["unifiedForecast"]["marks"] = marks
        detail["predictionMarks"] = detail["predictionMarks"][:4]
        detail["unifiedForecast"]["receiptSha256"] = _canonical_receipt(
            detail["unifiedForecast"])
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))

    def test_missing_ticket_plan_never_qualifies(self):
        detail = stored_detail()
        del detail["unifiedForecast"]["ticketPlan"]
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))

    def test_mark_blocks_disagreeing_never_qualify(self):
        detail = stored_detail()
        detail["unifiedForecast"]["marks"][0]["markSymbol"] = "○"
        detail["unifiedForecast"]["marks"][1]["markSymbol"] = "◎"
        self.assertIsNone(_ticket_pool4_upgrade_info(detail, NOW))


class TicketPool4ApplyTests(TestCase):
    def _upgrade(self, detail=None):
        detail = detail if detail is not None else stored_detail()
        info = _ticket_pool4_upgrade_info(detail, NOW)
        self.assertIsNotNone(info)
        info["receipt"] = detail["unifiedForecast"]["receiptSha256"]
        return detail, _apply_ticket_pool4_upgrade(
            detail, info, NOW.isoformat(timespec="seconds"))

    def test_trifecta_narrowed_to_canonical_pool4(self):
        _old, upgraded = self._upgrade()
        self.assertIsNotNone(upgraded)
        new, _receipt = upgraded
        trifecta = next(b for b in new["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 12)
        self.assertEqual({tuple(c) for c in trifecta["combos"]},
                         set(formation_pool4_axis2_selections(MARK_ORDER)))
        star = MARK_ORDER[4]
        for combo in trifecta["combos"]:
            self.assertNotIn(star, combo)
        # The prediction mirror carries the same narrowed list.
        self.assertEqual(new["prediction"]["recommendedBets"],
                         new["recommendedBets"])
        # The unified ticket plan's ☆-legged items are gone; the
        # clean trifecta items and the other kinds stay.
        items = new["unifiedForecast"]["ticketPlan"]["items"]
        self.assertEqual([i["combo"] for i in items
                          if i["kind"] == "3連単"], [[2, 1, 3], [1, 2, 5]])
        self.assertEqual([i["combo"] for i in items
                          if i["kind"] == "馬連"], [[2, 1]])

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
        self.assertEqual(
            next(b for b in new["recommendedBets"] if b["kind"] == "ワイド"),
            next(b for b in old["recommendedBets"] if b["kind"] == "ワイド"))
        self.assertEqual(new["horses"], old["horses"])
        # The receipt is re-sealed over the modified unified product.
        self.assertEqual(receipt,
                         _canonical_receipt(new["unifiedForecast"]))
        self.assertNotEqual(receipt, old["unifiedForecast"]["receiptSha256"])

    def test_revision_and_formation_stamped(self):
        old, (new, _receipt) = self._upgrade()
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["firstPublishedAt"], PUBLISHED_AT)
        self.assertEqual(marker["ticketFormation"],
                         {"formation": "P4A2", "scope": "nar-only"})
        revision = marker["revision"]
        self.assertEqual(revision["kind"], "ticket-pool4-upgrade")
        self.assertEqual(revision["reason"], "ticket-pool4-upgrade")
        self.assertEqual(revision["revisionCount"], 1)
        self.assertEqual(revision["previousReceiptSha256"],
                         old["unifiedForecast"]["receiptSha256"])
        self.assertEqual(revision["abilityLane"], V9B_LANE)

    def test_exactly_once(self):
        _old, (new, _receipt) = self._upgrade()
        self.assertIsNone(_ticket_pool4_upgrade_info(new, NOW))

    def test_apply_fails_closed_on_unexpected_combos(self):
        detail = stored_detail(combos=[[1, 2, 3], [2, 3, 1], [3, 1, 2],
                                       [1, 3, 2], [2, 1, 3], [3, 2, 1]])
        info = {"publishedAt": PUBLISHED_AT,
                "firstPublishedAt": PUBLISHED_AT,
                "previousAbilityLane": V9B_LANE,
                "reason": "ticket-pool4-upgrade",
                "markOrder": MARK_ORDER, "receipt": "x" * 64}
        self.assertIsNone(_apply_ticket_pool4_upgrade(
            detail, info, NOW.isoformat(timespec="seconds")))


class TicketPool4BuildGateTests(TestCase):
    def test_build_reissues_frozen_nar_r24_with_pool4(self):
        detail = stored_detail()
        summary = {"race_id": RACE_ID, "id": RACE_ID}
        new, receipt = build_publish_detail(
            copy.deepcopy(detail), summary, NOW)
        self.assertIsNotNone(new)
        trifecta = next(b for b in new["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 12)
        marker = new["preparedMeta"]["rewritePublish"]
        self.assertEqual(marker["revision"]["kind"],
                         "ticket-pool4-upgrade")
        self.assertEqual(marker["ticketFormation"],
                         {"formation": "P4A2", "scope": "nar-only"})
        self.assertEqual(receipt, new["unifiedForecast"]["receiptSha256"])
        self.assertEqual(new["predictionMarks"], detail["predictionMarks"])
        self.assertEqual(new["unifiedForecast"]["diagnosis"],
                         detail["unifiedForecast"]["diagnosis"])

    def test_build_leaves_jra_r24_frozen_detail_alone(self):
        detail = stored_detail(race_id=JRA_FROZEN_ID)
        new, reason = build_publish_detail(
            copy.deepcopy(detail),
            {"race_id": JRA_FROZEN_ID, "id": JRA_FROZEN_ID}, NOW)
        self.assertIsNone(new)
        self.assertTrue(str(reason).startswith("frozen:"), reason)


def _fresh_build(detail, summary, race, extras):
    with patch("scripts.arvexq_rewrite_publish.normalize_race",
               return_value=race), \
            patch("scripts.arvexq_rewrite_publish.forecast_race_v8",
                  return_value=v8_forecast()), \
            patch("scripts.arvexq_rewrite_publish._load_v8_extras",
                  return_value=extras):
        return build_publish_detail(detail, summary, FRESH_NOW)


def _mark_order_of(detail):
    symbols = ("◎", "○", "▲", "△", "☆")
    by_symbol = {e["markSymbol"]: e["horseNumber"]
                 for e in detail["unifiedForecast"]["marks"]}
    return [by_symbol[s] for s in symbols if s in by_symbol]


class FreshPublicationFormationTests(TestCase):
    def test_formation_constant(self):
        self.assertEqual(NAR_TRIFECTA_FORMATION, "P4A2")

    def test_nar_fresh_publication_builds_pool4(self):
        new, receipt = _fresh_build(
            fresh_detail(),
            {"race_id": "nar-2026-11-04-金沢-01",
             "id": "nar-2026-11-04-金沢-01"},
            fabricated_race(), NAR_EXTRAS)
        self.assertIsNotNone(new, receipt)
        marks = _mark_order_of(new)
        self.assertEqual(len(marks), 5)
        trifecta = next(b for b in new["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 12)
        self.assertEqual({tuple(c) for c in trifecta["combos"]},
                         set(formation_pool4_axis2_selections(marks)))
        self.assertEqual(
            new["preparedMeta"]["rewritePublish"]["ticketFormation"],
            {"formation": "P4A2", "scope": "nar-only"})
        self.assertIsNotNone(verified_unified(new))

    def test_jra_fresh_publication_stays_r24(self):
        detail = fresh_detail()
        detail["id"] = JRA_RACE_ID
        detail["circuit"] = "中央"
        detail["track"] = "東京"
        race = dataclasses.replace(
            fabricated_race(), race_id=JRA_RACE_ID,
            circuit=obs("中央", "test"), segment=Segment.JRA_FLAT)
        new, receipt = _fresh_build(
            detail, {"race_id": JRA_RACE_ID, "id": JRA_RACE_ID},
            race, JRA_EXTRAS)
        self.assertIsNotNone(new, receipt)
        marks = _mark_order_of(new)
        self.assertEqual(len(marks), 5)
        trifecta = next(b for b in new["recommendedBets"]
                        if b["kind"] == "3連単")
        self.assertEqual(trifecta["points"], 24)
        self.assertEqual({tuple(c) for c in trifecta["combos"]},
                         set(formation_r24_selections(marks)))
        self.assertNotIn("ticketFormation",
                         new["preparedMeta"]["rewritePublish"])
        self.assertIsNotNone(verified_unified(new))
