"""Sealed-product restore for projection tombstones (2026-11-23).

During the 2026-11-23 morning recovery, published races' STORED
details were overwritten with the API projection's shape
(predictionStatus "disabled" / predictionModelVersion
"arvexq-prediction-removed", forecast blocks stripped) while the
sealed unified product and the publish marker survived in the same
detail.  The protect guard's only restore source was the pre-off
archive in the worker's read envelope — absent from the stored
detail — so both lanes failed closed:

- rewrite-publish: 11 races failed with "stored forecast is
  tombstoned in the API projection and carries no verified pre-off
  archive";
- result repair: "D1 display view could not restore the tombstoned
  forecast: jra-2026-11-23-東京-03" (three attempts, no D1 post).

These tests pin the fix (scripts/arvexq_sealed_restore.py plus the
guard seams in scripts/arvexq_protect_sync.py):

- a tombstoned detail whose sealed product verifies (receipt ==
  marker receipt) is restored: predictionMarks verbatim from the
  product, stage probabilities from the product's diagnosis, and
  recommendedBets regenerated with the lane's own ticket generator,
  self-checked against the sealed ticketPlan;
- races that were never published need no exception: their stored
  details carry the prepared status stamps, not the projection's
  (verified against the stored 2026-11-23 Tokyo 1R / 5R and
  Fukushima 5R details), so the tombstone branch never engages;
- anything unverifiable still fails closed.
"""
from __future__ import annotations

import io
import json
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from arvexq.prediction.unified_product import (
    MODEL_VERSION, VERSION, canonical_receipt, verified, verified_sealed)
from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.tickets import generate_tickets
from rewrite.safety.probability import distribution, marginals
from scripts import arvexq_protect_sync as protect_sync
from scripts.arvexq_protect_sync import (
    _fetch_display_restored, _projection_tombstone, guard, protect_detail)
from scripts.arvexq_sealed_restore import sealed_product_restore

RID = "nar-2026-11-23-金沢-02"
DATE = "2026-11-23"
CAPTURED = "2026-11-23T10:32:00+09:00"
WIN = {1: 0.34, 2: 0.22, 3: 0.15, 4: 0.11, 5: 0.08, 6: 0.05, 7: 0.03, 8: 0.02}
LABELS = ["◎", "○", "▲", "△", "☆"]
COMBO_KINDS = {"wide": "ワイド", "quinella": "馬連", "exacta": "馬単",
               "trio": "3連複", "trifecta": "3連単"}


def _top3() -> dict[int, float]:
    outcomes = distribution(dict(WIN))
    return {n: round(values[2], 4) for n, values in marginals(outcomes).items()}


def _runners(top3: dict[int, float]) -> tuple:
    marks = {n: LABELS[i] for i, n in enumerate(sorted(WIN, key=lambda n: -WIN[n])[:5])}
    return tuple(
        RunnerForecast(
            number=n, name=f"H{n}", ability_score=0.5, strength=WIN[n],
            pace_adjustment=0.0, pace_reasons=(), p_win=WIN[n],
            p_top2=None, p_top3=top3[n], mark=marks.get(n, ""), status="ok")
        for n in sorted(WIN))


def _ticket_plan_items(top3: dict[int, float]) -> list:
    forecast = RaceForecast(race_id=RID, beta=0.0,
                            probability_status="calibrated-market-blend-v9b",
                            runners=_runners(top3), status="ok")
    plan = generate_tickets(forecast, {}, calibration_validated=False,
                            trifecta_formation="P4A2", place_odds={})
    by_kind: dict[str, list] = {}
    for ticket in plan.probability_tickets:
        if ticket.kind in COMBO_KINDS:
            by_kind.setdefault(COMBO_KINDS[ticket.kind], []).append(ticket)
    items = []
    for kind, cap in (("ワイド", 3), ("馬連", 2)):
        for ticket in by_kind.get(kind, [])[:cap]:
            items.append({"kind": kind, "combo": list(ticket.selection),
                          "probability": ticket.probability})
    return items


def _product() -> dict:
    top3 = _top3()
    ranked = sorted(WIN, key=lambda n: -WIN[n])
    product = {
        "version": VERSION, "raceId": RID, "raceDate": DATE,
        "circuit": "地方", "modelVersion": MODEL_VERSION,
        "modelFamily": "flat", "researchOnly": True,
        "probabilitiesCalibrated": False, "capturedAt": CAPTURED,
        "trainedThrough": "2026-11-01", "forecastStatus": "ok",
        "probabilityStatus": "calibrated-market-blend-v9b",
        "honmeiHorseNumber": ranked[0],
        "roster": [{"horseNumber": n, "name": f"H{n}"} for n in sorted(WIN)],
        "marks": [{"horseNumber": n, "markSymbol": LABELS[i],
                   "winProbability": WIN[n], "top3Probability": top3[n]}
                  for i, n in enumerate(ranked[:5])],
        "diagnosis": [{"horseNumber": n, "abilityScore": 0.5,
                       "winProbability": WIN[n], "top3Probability": top3[n],
                       "grade": "B", "reason": "fixture"}
                      for n in sorted(WIN)],
        "ticketPlan": {"items": _ticket_plan_items(top3)},
        "modelHash": "b" * 64,
    }
    product["receiptSha256"] = canonical_receipt(product)
    return product


def _marker(product: dict) -> dict:
    return {"modelVersion": MODEL_VERSION, "publishedAt": CAPTURED,
            "receiptSha256": product["receiptSha256"],
            "abilityLane": "v9b-cal-market", "temperature": 0.6692,
            "blendApplied": True,
            "ticketFormation": {"formation": "P4A2", "scope": "nar-only"}}


def _tombstoned(product: dict | None = None, marker: dict | None = None) -> dict:
    product = _product() if product is None else product
    detail = {
        "id": RID, "date": DATE, "circuit": "地方", "track": "金沢",
        "startTime": "13:55",
        "horses": [{"horseNumber": n, "name": f"H{n}"} for n in sorted(WIN)],
        "forecastText": "展開テキスト",
        "predictionStatus": "disabled",
        "predictionModelVersion": "arvexq-prediction-removed",
        "unifiedForecast": product,
        "preparedMeta": {"rewritePublish": _marker(product) if marker is None else marker},
    }
    assert verified(detail) is not None
    assert _projection_tombstone(detail)
    return detail


def _result_write(detail: dict) -> dict:
    write = deepcopy(detail)
    write["result"] = {"status": "確定",
                       "finishers": [{"horseNumber": 1, "position": 1},
                                     {"horseNumber": 2, "position": 2},
                                     {"horseNumber": 3, "position": 3}]}
    return write


class SealedProductRestoreTest(TestCase):
    def test_restore_rebuilds_blocks_from_sealed_product(self):
        detail = _tombstoned()
        restored = sealed_product_restore(detail)
        self.assertIsNotNone(restored)
        self.assertFalse(_projection_tombstone(restored))
        self.assertEqual(restored["predictionStatus"], "ready")
        self.assertEqual(restored["predictionModelVersion"], MODEL_VERSION)
        product = detail["unifiedForecast"]
        self.assertEqual(
            restored["predictionMarks"],
            [{"horseNumber": m["horseNumber"], "mark": m["markSymbol"],
              "winProbability": m["winProbability"]}
             for m in product["marks"]])
        win = restored["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertEqual(win, {str(n): WIN[n] for n in sorted(WIN)})
        bets = {(g["kind"], tuple(c)) for g in restored["recommendedBets"]
                for c in g["combos"]}
        for item in product["ticketPlan"]["items"]:
            self.assertIn((item["kind"], tuple(item["combo"])), bets)
        self.assertTrue(protect_sync._authorized_forecast(restored))

    def test_restore_rejects_marker_receipt_mismatch(self):
        product = _product()
        marker = _marker(product)
        marker["receiptSha256"] = "c" * 64
        self.assertIsNone(sealed_product_restore(_tombstoned(product, marker)))

    def test_restore_rejects_tampered_product(self):
        detail = _tombstoned()
        detail["unifiedForecast"]["diagnosis"][0]["winProbability"] = 0.99
        self.assertIsNone(verified(detail))
        self.assertIsNone(sealed_product_restore(detail))

    def test_restore_rejects_ticketplan_that_disagrees_with_regeneration(self):
        product = _product()
        items = product["ticketPlan"]["items"]
        items[0], items[1] = items[1], items[0]  # break the sealed ranking head
        product["receiptSha256"] = canonical_receipt(product)
        detail = _tombstoned(product)
        self.assertIsNotNone(verified(detail))  # internally consistent seal
        self.assertIsNone(sealed_product_restore(detail))  # but not the lane's ranking

    def test_restore_ignores_healthy_detail(self):
        detail = _tombstoned()
        detail["predictionStatus"] = "ready"
        detail["predictionModelVersion"] = MODEL_VERSION
        self.assertIsNone(sealed_product_restore(detail))

    def test_restore_with_scratched_runner_on_card(self):
        # Fukushima 3R (2026-11-23): the card keeps the scratched
        # runner, the sealed diagnosis covers only the 14 active
        # runners of 15 carded. The restore follows the product's
        # runner set, not the card.
        detail = _tombstoned()
        detail["horses"].append(
            {"horseNumber": 9, "name": "H9", "status": "出走取消"})
        self.assertIsNotNone(verified(detail))
        restored = sealed_product_restore(detail)
        self.assertIsNotNone(restored)
        win = restored["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertEqual(set(win), {str(n) for n in sorted(WIN)})

    def test_restore_with_post_sealing_scratch_in_roster(self):
        # Mizusawa 9R (2026-11-23): #3 was scratched AFTER the product
        # was sealed, so the sealed roster (and diagnosis) still
        # carries it while the card marks it inactive.  verified()
        # binds the roster to the ACTIVE runners and rightly stops
        # authorizing the forecast as current — but the seal itself
        # is intact, and the restore rebuilds the pre-off record,
        # so it must accept the product via verified_sealed.
        detail = _tombstoned()
        for horse in detail["horses"]:
            if horse["horseNumber"] == 8:
                horse["status"] = "出走取消"
                horse["scratched"] = True
        self.assertIsNone(verified(detail))
        self.assertIsNotNone(verified_sealed(detail))
        restored = sealed_product_restore(detail)
        self.assertIsNotNone(restored)
        win = restored["prediction"]["stages"]["probability"]["value"]["win"]
        self.assertEqual(set(win), {str(n) for n in sorted(WIN)})

    def test_restore_rejects_roster_horse_removed_from_card(self):
        # The sealed binding still requires the card and the roster
        # to name the same runners: a roster horse missing from the
        # card entirely is not a scratch, it is a different card.
        detail = _tombstoned()
        detail["horses"] = [h for h in detail["horses"]
                             if h["horseNumber"] != 8]
        self.assertIsNone(verified_sealed(detail))
        self.assertIsNone(sealed_product_restore(detail))

    def test_restore_rejects_renamed_card_horse(self):
        detail = _tombstoned()
        for horse in detail["horses"]:
            if horse["horseNumber"] == 8:
                horse["name"] = "H8-renamed"
        self.assertIsNone(verified_sealed(detail))
        self.assertIsNone(sealed_product_restore(detail))

    def test_restore_surgical_revision_marker(self):
        # Mizusawa 8R (2026-11-23): the place-EV upgrade re-sealed
        # the product in place (ticketPlan gained placeExpectedValues,
        # receipt changed) while capturedAt stayed at the first
        # publication; the marker's publishedAt advanced to the
        # revision time and its firstPublishedAt points at the
        # product's capturedAt.  The restore must accept that chain.
        product = _product()
        product["ticketPlan"]["placeExpectedValues"] = [
            {"horseNumber": 1, "top3Probability": 0.9,
             "placeOddsLow": 1.5, "placeOddsHigh": 2.0,
             "expectedValueLow": 1.35, "expectedValueHigh": 1.8}]
        product["receiptSha256"] = canonical_receipt(product)
        marker = _marker(product)
        marker["publishedAt"] = "2026-11-23T13:38:24+09:00"
        marker["firstPublishedAt"] = CAPTURED
        marker["revision"] = {
            "kind": "place-ev-upgrade", "reason": "place-ev-upgrade",
            "revisedAt": "2026-11-23T13:38:24+09:00", "revisionCount": 1,
            "previousReceiptSha256": "a" * 64}
        detail = _tombstoned(product, marker)
        self.assertIsNotNone(sealed_product_restore(detail))

    def test_restore_rejects_marker_with_unrelated_timestamps(self):
        # Receipt matches but neither publication stamp names the
        # product's capture: the marker belongs to another chain.
        product = _product()
        marker = _marker(product)
        marker["publishedAt"] = "2026-11-23T13:38:24+09:00"
        marker["firstPublishedAt"] = "2026-11-23T09:00:00+09:00"
        self.assertIsNone(sealed_product_restore(_tombstoned(product, marker)))

    def test_restore_prior_lane_shape(self):
        # Fukushima 4R (2026-11-23, jumps): published by the v1-prior
        # lane. The restored prediction carries that lane's shape.
        product = _product()
        marker = _marker(product)
        marker["abilityLane"] = "v1-prior"
        restored = sealed_product_restore(_tombstoned(product, marker))
        self.assertIsNotNone(restored)
        prediction = restored["prediction"]
        self.assertEqual(prediction["methodologyStatus"],
                         "rewrite-engine-probability-uncalibrated")
        self.assertEqual(prediction["calibrationMethod"],
                         "none-probabilities-uncalibrated")
        self.assertEqual(prediction["stages"]["ability"]["status"],
                         "rewrite-ability-prior-v1")

    def test_restore_unknown_lane_fails_closed(self):
        product = _product()
        marker = _marker(product)
        marker["abilityLane"] = "some-future-lane"
        self.assertIsNone(sealed_product_restore(_tombstoned(product, marker)))


class ProtectDetailSeamTest(TestCase):
    def test_result_write_over_tombstone_restores_forecast(self):
        old = _tombstoned()
        out = protect_detail(old, _result_write(old))
        self.assertFalse(_projection_tombstone(out))
        self.assertEqual(out["predictionStatus"], "ready")
        self.assertEqual(len(out["predictionMarks"]), 5)
        self.assertTrue(out["recommendedBets"])
        self.assertEqual(out["result"]["status"], "確定")

    def test_result_write_over_post_sealing_scratch_tombstone_restores(self):
        # The Mizusawa 9R seam exactly as the lanes hit it: the
        # publish lane's protect_detail(old_raw, new) raised the
        # tombstone error because the sealed restore inside it
        # rejected the product over the post-sealing scratch.
        old = _tombstoned()
        for horse in old["horses"]:
            if horse["horseNumber"] == 8:
                horse["status"] = "出走取消"
                horse["scratched"] = True
        out = protect_detail(old, _result_write(old))
        self.assertFalse(_projection_tombstone(out))
        self.assertEqual(out["predictionStatus"], "ready")
        self.assertEqual(len(out["predictionMarks"]), 5)
        self.assertEqual(out["result"]["status"], "確定")

    def test_never_published_prepared_detail_is_not_a_tombstone(self):
        # The real "no forecast" races (unpublished Tokyo 1R / 5R and
        # Fukushima 5R on 2026-11-23) store the prepared detail: its
        # status reads "disabled" but the model version is NOT the
        # projection's removal stamp, so the tombstone branch is
        # never entered and a result write is judged normally.
        old = _tombstoned()
        del old["unifiedForecast"]
        del old["preparedMeta"]
        old["predictionModelVersion"] = "arvexq-prepared-detail"
        self.assertFalse(_projection_tombstone(old))
        out = protect_detail(old, _result_write(old))
        self.assertEqual(out["result"]["status"], "確定")

    def test_unverifiable_tombstone_still_fails_closed(self):
        old = _tombstoned()
        old["unifiedForecast"]["diagnosis"][0]["winProbability"] = 0.99
        with self.assertRaises(RuntimeError):
            protect_detail(old, _result_write(old))

    def test_guard_refuses_to_emit_projection_over_sealed_forecast(self):
        detail = _tombstoned()
        body = {"details": [deepcopy(detail)]}
        with self.assertRaises(RuntimeError):
            guard(body, read=lambda base, rid: None, base="https://example.invalid")


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


class FetchDisplayRestoredTest(TestCase):
    def _fetch_with(self, candidate: dict):
        with patch("urllib.request.urlopen",
                   return_value=_FakeResponse({"detail": candidate})):
            return _fetch_display_restored("https://example.invalid", RID)

    def test_display_tombstone_is_restored_from_sealed_product(self):
        restored = self._fetch_with(_tombstoned())
        self.assertFalse(_projection_tombstone(restored))
        self.assertEqual(restored["predictionStatus"], "ready")
        self.assertEqual(len(restored["predictionMarks"]), 5)

    def test_display_prepared_detail_is_returned_as_stored_state(self):
        candidate = _tombstoned()
        del candidate["unifiedForecast"]
        del candidate["preparedMeta"]
        candidate["predictionModelVersion"] = "arvexq-prepared-detail"
        self.assertEqual(self._fetch_with(candidate), candidate)

    def test_display_unverifiable_tombstone_fails_closed(self):
        candidate = _tombstoned()
        candidate["unifiedForecast"]["diagnosis"][0]["winProbability"] = 0.99
        with self.assertRaises(RuntimeError):
            self._fetch_with(candidate)


class ConstantPinTest(TestCase):
    def test_mirrored_constants_match_publish_lane(self):
        from scripts import arvexq_rewrite_publish as publish
        from scripts import arvexq_sealed_restore as restore
        self.assertEqual(restore.ABILITY_STATUS_V9B, publish.V9B_ABILITY_STATUS)
        self.assertEqual(restore.ABILITY_STATUS_V8, publish.V8_ABILITY_STATUS)
        self.assertEqual(restore.COMBO_KINDS, publish.COMBO_KINDS)
        self.assertEqual(restore.LANE_SHAPES[publish.V9B_LANE][2],
                         publish.V9B_ABILITY_STATUS)


if __name__ == "__main__":
    import unittest
    unittest.main()
