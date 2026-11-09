"""Regression: published recommendedBets must survive later sync writes.

2026-10-31 incident: the rewrite publish lane wrote the full forecast
blocks (predictionStatus 'ready', grouped recommendedBets incl. the
36-point trifecta formation B) into D1, but later prefetch writes —
whose details inherit preparedMeta.rewritePublish from their stored
seed while passing through the display compaction that strips the bet
blocks — overwrote them, because protect_detail trusted the marker
alone. The app then fell back to the <=5-item ticketPlan and the
trifecta never appeared in the おすすめ買い目 tab.

These tests pin the two fixed behaviours:
- protect_detail restores the forecast blocks from the stored detail
  unless the incoming write is a COMPLETE publish-lane write (marker
  AND every forecast block present);
- public_race's verified-unified projection carries the stored grouped
  recommendedBets instead of replacing them with [].
"""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from unittest import TestCase

from arvexq.forecast.publication import public_race
from arvexq.prediction.unified_product import MODEL_VERSION, VERSION, race_family
from scripts.arvexq_protect_sync import protect_detail

FORECAST_KEYS = ("unifiedForecast", "prediction", "predictionMarks",
                 "recommendedBets", "forecastText", "predictionStatus",
                 "predictionModelVersion", "preRaceBet")
BETS = [
    {"kind": "ワイド", "combos": [[8, 5]], "points": 1, "reason": "r"},
    {"kind": "3連単", "combos": [[8, 5, 2]] * 36, "points": 36, "reason": "r"},
]


def _stored_publish_detail() -> dict:
    return {
        "id": "nar-2026-10-31-高知-12", "date": "2026-10-31",
        "preparedMeta": {"rewritePublish": {
            "modelVersion": MODEL_VERSION,
            "publishedAt": "2026-10-31T11:49:20+09:00",
            "receiptSha256": "x" * 64}},
        "unifiedForecast": {"version": VERSION},
        "prediction": {"modelVersion": MODEL_VERSION},
        "predictionMarks": [{"horseNumber": 8, "mark": "◎"}],
        "recommendedBets": deepcopy(BETS),
        "forecastText": "text",
        "predictionStatus": "ready",
        "predictionModelVersion": MODEL_VERSION,
        "preRaceBet": {"decision": "推奨", "items": deepcopy(BETS)},
        "horses": [],
    }


class ProtectDetailBetsVisibilityTests(TestCase):
    def test_marker_inheriting_stripped_write_restores_bets(self):
        old = _stored_publish_detail()
        incoming = {
            "id": old["id"], "date": old["date"],
            # Marker inherited from the stored seed; bet blocks stripped
            # by the display compaction, status forced to disabled.
            "preparedMeta": deepcopy(old["preparedMeta"]),
            "predictionStatus": "disabled",
            "unifiedForecast": {"version": VERSION},
            "horses": [],
        }
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["predictionStatus"], "ready")
        self.assertEqual(out["recommendedBets"], BETS)
        self.assertEqual(out["preRaceBet"]["items"], BETS)
        for key in FORECAST_KEYS:
            self.assertIn(key, out)

    def test_complete_publish_write_still_replaces(self):
        old = _stored_publish_detail()
        incoming = _stored_publish_detail()
        incoming["recommendedBets"] = [
            {"kind": "3連単", "combos": [[1, 2, 3]], "points": 1,
             "reason": "new"}]
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["recommendedBets"], incoming["recommendedBets"])

    def test_unmarked_write_still_restores(self):
        old = _stored_publish_detail()
        incoming = {"id": old["id"], "date": old["date"],
                    "predictionStatus": "disabled", "horses": []}
        out = protect_detail(deepcopy(old), deepcopy(incoming))
        self.assertEqual(out["recommendedBets"], BETS)


def _verified_detail(with_bets: bool) -> dict:
    horses = [{"horseNumber": i, "name": f"馬{i}"} for i in range(1, 9)]
    race = {
        "id": "nar-2026-11-01-高知-01", "date": "2026-11-01",
        "circuit": "地方", "track": "高知", "surface": "ダート",
        "title": "一般", "startTime": "20:50", "horses": horses,
    }
    unified = {
        "version": VERSION, "raceId": race["id"], "raceDate": race["date"],
        "circuit": "地方", "modelVersion": MODEL_VERSION,
        "modelFamily": race_family(race), "researchOnly": True,
        "probabilitiesCalibrated": False,
        "capturedAt": "2026-11-01T09:00:00+09:00",
        "trainedThrough": "2026-10-23",
        "roster": [{"horseNumber": h["horseNumber"], "name": h["name"]}
                   for h in horses],
        "marks": [{"horseNumber": 1, "markSymbol": "◎"},
                  {"horseNumber": 2, "markSymbol": "○"}],
        "pace": {"text": "展開テキスト"},
        "ticketPlan": {"items": [], "sameModelAndMarks": True},
    }
    canonical = {k: v for k, v in unified.items() if k != "receiptSha256"}
    unified["receiptSha256"] = sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    detail = dict(race, unifiedForecast=unified)
    if with_bets:
        detail["recommendedBets"] = deepcopy(BETS)
    return detail


class PublicRaceBetsVisibilityTests(TestCase):
    def test_verified_projection_carries_grouped_bets(self):
        result = public_race(_verified_detail(with_bets=True))
        self.assertEqual(result["predictionStatus"],
                         "unified-reference-ready")
        self.assertEqual(result["recommendedBets"], BETS)
        self.assertIn("recommendedBetPlan", result)

    def test_verified_projection_without_source_bets_stays_empty(self):
        result = public_race(_verified_detail(with_bets=False))
        self.assertEqual(result["recommendedBets"], [])
