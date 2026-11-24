"""Static API pack builder: forecast carry-over guard.

Regression for the 2026-11-24 pack incident: a full build regenerates
details from the analyzed prefetch payload (no forecast blocks for any
race), and the publish lane's merge step only re-overlays the races
the current run (re)published — so races published by earlier runs
and frozen since lost their sealed forecast blocks in the pack
(predictionStatus "disabled", blocks stripped) while the lane counted
them published.  The build must carry the sealed blocks over from the
existing pack instead of stripping them, and must not invent blocks
for races that were never published.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import arvexq_static_api_build as b

DATE = "2026-11-24"
RID1 = f"nar-{DATE}-水沢-01"
RID2 = f"nar-{DATE}-水沢-02"

PRODUCT = {"version": "arvexq-unified-product-v1", "raceId": RID1,
           "receiptSha256": "a" * 64, "marks": [], "diagnosis": []}
MARKER = {"modelVersion": "arvexq-rewrite-v3-v9b",
          "receiptSha256": "a" * 64, "abilityLane": "v9b-cal-market",
          "publishedAt": "2026-11-24T07:32:15+09:00"}


def summary(rid):
    return {"id": rid, "date": DATE, "circuit": "地方", "track": "水沢",
            "raceNumber": 1, "startTime": "11:00", "title": "1R",
            "surface": "ダート", "distance": 1300, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": "", "updatedAtEpoch": 0}


def published_detail(rid):
    return {
        "id": rid, "date": DATE, "track": "水沢", "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲"},
                   {"horseNumber": 2, "name": "乙"}],
        "predictionStatus": "ready",
        "predictionModelVersion": "arvexq-rewrite-v3-v9b",
        "unifiedForecast": dict(PRODUCT, raceId=rid),
        "prediction": {"predictionStatus": "ready"},
        "predictionMarks": [{"horseNumber": 1, "mark": "◎",
                             "winProbability": 0.4}],
        "recommendedBets": [{"kind": "ワイド", "combos": [[1, 2]],
                             "points": 1}],
        "forecastText": "先行馬中心。",
        "preparedMeta": {"diagnosisReady": True,
                         "rewritePublish": dict(MARKER)},
    }


def projection_detail(rid):
    """The analyzed prefetch payload's shape: card data, no forecast."""
    return {
        "id": rid, "date": DATE, "track": "水沢", "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲"},
                   {"horseNumber": 2, "name": "乙"}],
        "predictionStatus": "disabled",
        "preparedMeta": {"diagnosisReady": True},
    }


def sync_payload(details):
    return {"summaries": [summary(d["id"]) for d in details],
            "details": details, "odds_current": []}


def read_pack(out_dir, rid):
    body = json.loads((Path(out_dir) / "race" / f"{rid}.json")
                      .read_text(encoding="utf-8"))
    return body["detail"]


class ForecastCarryoverTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"

    def tearDown(self):
        self._tmp.cleanup()

    def _seed_existing(self, details):
        model = b.model_from_sync_payload(sync_payload(details))
        b.build(model, self.out, "2026-11-24T07:00:00+09:00")

    def test_full_build_keeps_published_forecast_blocks(self):
        self._seed_existing([published_detail(RID1)])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)]))
        healed = b.carry_over_forecast_blocks(incoming, self.out)
        self.assertEqual(healed, [RID1])
        b.build(incoming, self.out, "2026-11-24T12:00:00+09:00")
        detail = read_pack(self.out, RID1)
        self.assertEqual(detail["predictionStatus"], "ready")
        self.assertEqual(detail["unifiedForecast"]["receiptSha256"],
                         "a" * 64)
        self.assertEqual(detail["predictionMarks"],
                         [{"horseNumber": 1, "mark": "◎",
                           "winProbability": 0.4}])
        self.assertEqual(
            detail["preparedMeta"]["rewritePublish"]["receiptSha256"],
            "a" * 64)

    def test_never_published_race_stays_forecastless(self):
        self._seed_existing([projection_detail(RID2)])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID2)]))
        healed = b.carry_over_forecast_blocks(incoming, self.out)
        self.assertEqual(healed, [])
        b.build(incoming, self.out, "2026-11-24T12:00:00+09:00")
        detail = read_pack(self.out, RID2)
        self.assertNotIn("unifiedForecast", detail)
        self.assertEqual(detail["predictionStatus"], "disabled")

    def test_incoming_forecast_is_not_overwritten(self):
        self._seed_existing([published_detail(RID1)])
        own = published_detail(RID1)
        own["unifiedForecast"] = dict(PRODUCT, raceId=RID1,
                                       receiptSha256="b" * 64)
        incoming = b.model_from_sync_payload(sync_payload([own]))
        healed = b.carry_over_forecast_blocks(incoming, self.out)
        self.assertEqual(healed, [])
        self.assertEqual(
            incoming.details[RID1]["unifiedForecast"]["receiptSha256"],
            "b" * 64)


if __name__ == "__main__":
    unittest.main()
