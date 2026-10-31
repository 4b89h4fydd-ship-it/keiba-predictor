"""Regression: unified receipt verification must bind content, not spelling.

2026-10-31 incident: every stored race failed unified_product.verified()
after its payload crossed the JS boundary (the sync worker re-serializes
with JSON.stringify / JSON.parse). JS collapses integral floats to ints
(2.0 -> 2) and -0.0 to 0, so Python's type-sensitive canonical dumps
hashed a different string for identical content and public_race dropped
the race to predictionStatus='disabled' (pinpointed on the real stored
payload of jra-2026-10-31-東京-11, where beta 2.0 -> 2 was the only
difference from the sealed receipt).

These tests pin:
- a payload sealed with the value-canonical receipt verifies after a
  simulated JS round trip;
- a payload sealed with the LEGACY type-sensitive receipt (all rows
  stored before the fix) verifies both untouched and JS round-tripped;
- any actual content change (value, key, roster, ticket probability)
  still fails verification under every sealing style.
"""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from unittest import TestCase

from arvexq.prediction.unified_product import (
    MODEL_VERSION, VERSION, canonical_receipt, verified)


def _legacy_receipt(product: dict) -> str:
    canonical = {k: v for k, v in product.items() if k != "receiptSha256"}
    return sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def _js_round_trip(value):
    """What JSON.stringify + JSON.parse does to Python-native JSON data:
    integral floats become ints, -0.0 becomes 0; values are unchanged."""
    if isinstance(value, float):
        if value == 0:
            return 0
        if value.is_integer() and abs(value) < 2 ** 53:
            return int(value)
        return value
    if isinstance(value, dict):
        return {k: _js_round_trip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_js_round_trip(v) for v in value]
    return value


def _product() -> dict:
    return {
        "version": VERSION,
        "raceId": "jra-2026-10-31-東京-11",
        "raceDate": "2026-10-31",
        "circuit": "中央",
        "modelFamily": "flat",
        "specialHandling": "通常",
        "capturedAt": "2026-10-31T12:20:41+09:00",
        "trainedThrough": "2026-10-23",
        "modelVersion": MODEL_VERSION,
        # Integral floats on schema-float keys: the JS-collapse victims.
        "beta": 2.0,
        "roster": [{"horseNumber": n, "name": f"馬{n}"} for n in (1, 2, 3, 4)],
        "marks": [
            {"horseNumber": 2, "markSymbol": "◎", "winProbability": 0.4,
             "top3Probability": 0.75},
            {"horseNumber": 1, "markSymbol": "○", "winProbability": 0.25,
             "top3Probability": 0.6},
        ],
        "diagnosis": [
            {"horseNumber": 1, "abilityScore": 0.5, "winProbability": 0.25,
             "top3Probability": 0.6},
            {"horseNumber": 2, "abilityScore": 0.9, "winProbability": 0.4,
             "top3Probability": 0.75},
            {"horseNumber": 3, "abilityScore": 0.1, "winProbability": 0.2,
             "top3Probability": 0.5},
            {"horseNumber": 4, "abilityScore": 0.05, "winProbability": 0.15,
             "top3Probability": 0.45},
        ],
        "pace": {"pacePressure": 0.25, "text": "ハイペース想定"},
        "ticketPlan": {
            "items": [{"kind": "ワイド", "combo": [2, 1], "probability": 0.3}],
            "winExpectedValues": [
                {"horseNumber": 3, "winProbability": 0.2, "odds": 4.0,
                 "expectedValue": 0.8},
            ],
        },
        "researchOnly": True,
        "probabilitiesCalibrated": False,
        "humanOverrides": False,
    }


def _race(product: dict) -> dict:
    return {
        "id": "jra-2026-10-31-東京-11", "date": "2026-10-31",
        "track": "東京", "surface": "ダート", "title": "テストステークス",
        "circuit": "中央", "startTime": "15:30",
        "horses": [{"horseNumber": n, "name": f"馬{n}"} for n in (1, 2, 3, 4)],
        "unifiedForecast": product,
    }


def _sealed(seal) -> dict:
    product = _product()
    product["receiptSha256"] = seal(product)
    return _race(product)


class ReceiptCanonicalizationTests(TestCase):
    def test_value_canonical_seal_survives_js_round_trip(self):
        race = _sealed(canonical_receipt)
        self.assertIsNotNone(verified(race))
        self.assertIsNotNone(verified(_js_round_trip(race)))
        # Full text round trip as well (parse of the collapsed spelling).
        text = json.dumps(_js_round_trip(race), ensure_ascii=False)
        self.assertIsNotNone(verified(json.loads(text)))

    def test_legacy_seal_verifies_untouched_and_js_round_tripped(self):
        race = _sealed(_legacy_receipt)
        self.assertIsNotNone(verified(race))
        self.assertIsNotNone(verified(_js_round_trip(race)))

    def test_tampering_fails_under_every_sealing_style(self):
        tampers = {
            "probability changed": lambda p: p["marks"][0].update(
                winProbability=0.41),
            "beta value changed": lambda p: p.update(beta=4.0),
            "integral odds changed": lambda p: p["ticketPlan"][
                "winExpectedValues"][0].update(odds=5.0),
            "horse renamed": lambda p: p["roster"][0].update(name="別馬"),
            "key deleted": lambda p: p.pop("pace"),
            "key added": lambda p: p.update(extraField="x"),
            "ticket probability changed": lambda p: p["ticketPlan"][
                "items"][0].update(probability=0.31),
        }
        for seal in (canonical_receipt, _legacy_receipt):
            for name, mutate in tampers.items():
                with self.subTest(seal=seal.__name__, tamper=name):
                    race = _sealed(seal)
                    mutate(race["unifiedForecast"])
                    self.assertIsNone(verified(race))
                    self.assertIsNone(verified(_js_round_trip(race)))

    def test_receipt_itself_is_not_self_referential(self):
        race = _sealed(canonical_receipt)
        race["unifiedForecast"]["receiptSha256"] = "0" * 64
        self.assertIsNone(verified(race))
