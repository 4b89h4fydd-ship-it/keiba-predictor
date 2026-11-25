"""Static API pack builder: projection-status carry-over seam.

Regression for the second loss of the 2026-11-24 pack forecasts and
the 2026-11-25 recurrence: the result-ingest lane's payload details
pass through the delivery projection
(arvexq/forecast/publication.py), which renames a published detail's
predictionStatus to "unified-reference-ready" while keeping its
sealed forecast blocks.  The merge writes that status into the pack.
The forecast carry-over guard accepted only "ready" as a source
status, so the next forecast-less full build stripped the blocks of
every race the result lane had touched — and once stripped, the
pack's own "disabled" status disqualified it as a source forever.

Timeline pinned by the pack git history (Sonoda 1R, 2026-11-25):
ready 12:44 -> "unified-reference-ready" 12:45 (result ingest) ->
disabled 14:41 (lane direct full).  Same shape on 2026-11-24
(Nagoya 1R): restore "ready" 12:27 -> projection status 14:44 ->
stripped 15:23.

Also pins carry_over_day_statuses: lane payload summaries carry no
raceStatus, so a full build blanked every day row's published
status until the next result merge restored it.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import arvexq_static_api_build as b

DATE = "2026-11-25"
RID1 = f"nar-{DATE}-園田-01"

PRODUCT = {"version": "arvexq-unified-product-v1", "raceId": RID1,
           "receiptSha256": "a" * 64, "marks": [], "diagnosis": []}
MARKER = {"modelVersion": "arvexq-rewrite-v3-v9b",
          "receiptSha256": "a" * 64, "abilityLane": "v9b-cal-market",
          "publishedAt": "2026-11-25T07:32:15+09:00"}


def summary(rid, race_status=""):
    return {"id": rid, "date": DATE, "circuit": "地方", "track": "園田",
            "raceNumber": 1, "startTime": "11:00", "title": "1R",
            "surface": "ダート", "distance": 1400, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": race_status, "updatedAtEpoch": 0}


def published_detail(rid, status="ready"):
    return {
        "id": rid, "date": DATE, "track": "園田", "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲"},
                   {"horseNumber": 2, "name": "乙"}],
        "predictionStatus": status,
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
        "id": rid, "date": DATE, "track": "園田", "raceNumber": 1,
        "horses": [{"horseNumber": 1, "name": "甲"},
                   {"horseNumber": 2, "name": "乙"}],
        "predictionStatus": "disabled",
        "preparedMeta": {"diagnosisReady": True},
    }


def sync_payload(details, summaries=None):
    return {"summaries": summaries if summaries is not None
            else [summary(d["id"]) for d in details],
            "details": details, "odds_current": []}


def read_pack(out_dir, rid):
    body = json.loads((Path(out_dir) / "race" / f"{rid}.json")
                      .read_text(encoding="utf-8"))
    return body["detail"]


def read_day_row(out_dir, rid):
    day = json.loads((Path(out_dir) / "day" / f"{DATE}.json")
                     .read_text(encoding="utf-8"))
    return next(r for r in day["races"] if r["id"] == rid)


class ProjectionStatusCarryoverTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"

    def tearDown(self):
        self._tmp.cleanup()

    def _seed_existing(self, details, summaries=None):
        model = b.model_from_sync_payload(sync_payload(details, summaries))
        b.build(model, self.out, "2026-11-25T07:00:00+09:00")

    def test_projection_status_pack_is_a_carryover_source(self):
        # The state the result-ingest merge leaves behind: blocks
        # present, status renamed by the delivery projection.
        self._seed_existing(
            [published_detail(RID1, status="unified-reference-ready")])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)]))
        healed = b.carry_over_forecast_blocks(incoming, self.out)
        self.assertEqual(healed, [RID1])
        b.build(incoming, self.out, "2026-11-25T14:41:00+09:00")
        detail = read_pack(self.out, RID1)
        self.assertEqual(detail["predictionStatus"], "ready")
        self.assertEqual(detail["unifiedForecast"]["receiptSha256"],
                         "a" * 64)
        self.assertEqual(
            detail["preparedMeta"]["rewritePublish"]["receiptSha256"],
            "a" * 64)

    def test_disabled_pack_is_not_a_carryover_source(self):
        # A tombstoned pack must not resurrect blocks on its own:
        # even if a unifiedForecast dict were somehow present, a
        # non-published status is not a publication receipt.
        tombstone = published_detail(RID1, status="disabled")
        self._seed_existing([tombstone])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)]))
        healed = b.carry_over_forecast_blocks(incoming, self.out)
        self.assertEqual(healed, [])

    def test_ready_pack_still_heals(self):
        self._seed_existing([published_detail(RID1, status="ready")])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)]))
        healed = b.carry_over_forecast_blocks(incoming, self.out)
        self.assertEqual(healed, [RID1])


class DayStatusCarryoverTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"

    def tearDown(self):
        self._tmp.cleanup()

    def _seed_existing(self, details, summaries=None):
        model = b.model_from_sync_payload(sync_payload(details, summaries))
        b.build(model, self.out, "2026-11-25T07:00:00+09:00")

    def test_full_build_keeps_published_day_status(self):
        self._seed_existing([published_detail(RID1)],
                            summaries=[summary(RID1, "確定")])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)],
                         summaries=[summary(RID1, "")]))
        healed = b.carry_over_day_statuses(incoming, self.out)
        self.assertEqual(healed, [RID1])
        b.build(incoming, self.out, "2026-11-25T14:41:00+09:00")
        self.assertEqual(read_day_row(self.out, RID1)["raceStatus"],
                         "確定")

    def test_incoming_status_wins_over_existing(self):
        self._seed_existing([published_detail(RID1)],
                            summaries=[summary(RID1, "確定")])
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)],
                         summaries=[summary(RID1, "速報")]))
        healed = b.carry_over_day_statuses(incoming, self.out)
        self.assertEqual(healed, [])
        b.build(incoming, self.out, "2026-11-25T12:00:00+09:00")
        self.assertEqual(read_day_row(self.out, RID1)["raceStatus"],
                         "速報")

    def test_no_existing_pack_invents_nothing(self):
        incoming = b.model_from_sync_payload(
            sync_payload([projection_detail(RID1)],
                         summaries=[summary(RID1, "")]))
        healed = b.carry_over_day_statuses(incoming, self.out)
        self.assertEqual(healed, [])
        b.build(incoming, self.out, "2026-11-25T07:00:00+09:00")
        self.assertEqual(read_day_row(self.out, RID1)["raceStatus"], "")


if __name__ == "__main__":
    unittest.main()
