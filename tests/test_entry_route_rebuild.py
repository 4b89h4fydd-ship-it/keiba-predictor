"""Integration tests for the 2026-11-28 entry-route rebuild.

Covers the three structural fixes beyond the reconcile module's own
unit tests:

* the static build's forecast identity guard — a rebuild whose
  roster identity disagrees with the sealed pack must not overwrite
  the sealed forecast, while a genuine publish-lane re-issue
  (strictly newer marker) still wins;
* the static racecard manifest correction — a later, internally
  consistent roster replaces a garbled one for the same race
  (the old "first complete roster wins" rule locked the garble in);
* the prefetch recovery graft — a rescued roster may only lend its
  identity to a current card naming exactly the same horses, and a
  permuted-but-clean roster is not a usable card.
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts import arvexq_prefetch as prefetch
from scripts import arvexq_static_api_build as b
from scripts.arvexq_publish_racecards_static import (
    merge_manifest, racecard_manifest)

DATE = "2026-11-24"
RID = f"nar-{DATE}-水沢-01"
MARKER_OLD = {"modelVersion": "arvexq-rewrite-v3-v9b",
              "receiptSha256": "a" * 64, "abilityLane": "v9b-cal-market",
              "publishedAt": "2026-11-24T07:32:15+09:00"}
MARKER_NEW = dict(MARKER_OLD, receiptSha256="c" * 64,
                  publishedAt="2026-11-24T09:00:00+09:00")


def summary(rid):
    return {"id": rid, "date": DATE, "circuit": "地方", "track": "水沢",
            "raceNumber": 1, "startTime": "11:00", "title": "1R",
            "surface": "ダート", "distance": 1300, "weather": "晴",
            "condition": "良", "volatility": {"label": "", "score": None},
            "raceStatus": "", "updatedAtEpoch": 0}


def detail(rid, horses, receipt, marker):
    return {
        "id": rid, "date": DATE, "track": "水沢", "raceNumber": 1,
        "horses": horses,
        "predictionStatus": "ready",
        "predictionModelVersion": "arvexq-rewrite-v3-v9b",
        "unifiedForecast": {"version": "arvexq-unified-product-v1",
                            "raceId": rid, "receiptSha256": receipt,
                            "marks": [], "diagnosis": []},
        "prediction": {"predictionStatus": "ready"},
        "predictionMarks": [{"horseNumber": 1, "mark": "◎",
                             "winProbability": 0.4}],
        "recommendedBets": [],
        "forecastText": "先行馬中心。",
        "preparedMeta": {"diagnosisReady": True,
                         "rewritePublish": dict(marker)},
    }


def sync_payload(details):
    return {"summaries": [summary(d["id"]) for d in details],
            "details": details, "odds_current": []}


class ForecastIdentityGuardTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "packs"
        sealed = detail(RID, [{"horseNumber": 1, "name": "甲"},
                              {"horseNumber": 2, "name": "乙"}],
                        "a" * 64, MARKER_OLD)
        model = b.model_from_sync_payload(sync_payload([sealed]))
        b.build(model, self.out, "2026-11-24T07:00:00+09:00")

    def tearDown(self):
        self._tmp.cleanup()

    def test_permuted_rebuild_cannot_overwrite_sealed_forecast(self):
        incoming_detail = detail(
            RID, [{"horseNumber": 2, "name": "甲"},
                  {"horseNumber": 1, "name": "乙"}],
            "c" * 64, MARKER_OLD)  # pass-through marker, not a re-issue
        incoming = b.model_from_sync_payload(sync_payload([incoming_detail]))
        b.carry_over_forecast_blocks(incoming, self.out)
        kept = incoming.details[RID]
        self.assertEqual(kept["unifiedForecast"]["receiptSha256"], "a" * 64)

    def test_fresher_reissue_still_wins(self):
        incoming_detail = detail(
            RID, [{"horseNumber": 2, "name": "甲"},
                  {"horseNumber": 1, "name": "乙"}],
            "c" * 64, MARKER_NEW)
        incoming = b.model_from_sync_payload(sync_payload([incoming_detail]))
        b.carry_over_forecast_blocks(incoming, self.out)
        kept = incoming.details[RID]
        self.assertEqual(kept["unifiedForecast"]["receiptSha256"], "c" * 64)


def manifest_with_frames(frames, day="2026-10-10"):
    payload = {"summaries": [{"id": f"jra-{day}-東京-01", "date": day,
                              "circuit": "中央", "track": "東京",
                              "raceNumber": 1, "fieldSize": 3,
                              "title": "1R", "startTime": "10:05"}],
               "details": [{"id": f"jra-{day}-東京-01", "date": day,
                            "horses": [
                                {"horseNumber": 1, "frameNumber": frames[0],
                                 "name": "甲", "jockey": "A"},
                                {"horseNumber": 2, "frameNumber": frames[1],
                                 "name": "乙", "jockey": "B"},
                                {"horseNumber": 3, "frameNumber": frames[2],
                                 "name": "丙", "jockey": "C"}]}]}
    return racecard_manifest(payload)


class ManifestCorrectionTest(unittest.TestCase):
    def test_consistent_roster_replaces_frameless_garble(self):
        garbled = manifest_with_frames([0, 0, 0])
        correct = manifest_with_frames([1, 2, 3])
        merged = merge_manifest(garbled, correct)
        frames = [h["frameNumber"] for h in merged["races"][0]["horses"]]
        self.assertEqual(frames, [1, 2, 3])

    def test_frameless_reading_never_replaces_consistent_roster(self):
        correct = manifest_with_frames([1, 2, 3])
        garbled = manifest_with_frames([0, 0, 0])
        merged = merge_manifest(correct, garbled)
        frames = [h["frameNumber"] for h in merged["races"][0]["horses"]]
        self.assertEqual(frames, [1, 2, 3])


TRUE_FRAMES_13 = [1, 2, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8]


def jra_card(numbers, frames):
    return {"id": "jra-2026-11-28-京都-09", "circuit": "中央",
            "track": "京都", "date": "2026-11-28", "fieldSize": 13,
            "horses": [{"horseNumber": no, "frameNumber": fr,
                        "name": f"馬{i}", "jockey": "騎手",
                        "carriedWeight": 56}
                       for i, (no, fr) in enumerate(zip(numbers, frames))]}


class PrefetchRecoveryTest(unittest.TestCase):
    def test_permuted_clean_roster_is_not_usable(self):
        # Numbers rotated by one; the frames still describe the true
        # gates.  Clean permutation, scrambled identity: not usable.
        numbers = list(range(2, 14)) + [1]
        card = jra_card(numbers, TRUE_FRAMES_13)
        self.assertFalse(prefetch._card_usable(card))

    def test_true_card_is_usable(self):
        card = jra_card(list(range(1, 14)), TRUE_FRAMES_13)
        self.assertTrue(prefetch._card_usable(card))

    def test_recovered_identity_requires_same_name_set(self):
        current = {"id": "jra-2026-11-28-京都-09", "date": "2026-11-28",
                   "horses": [{"horseNumber": 9, "name": "甲",
                               "bodyWeight": 500},
                              {"horseNumber": 7, "name": "乙"}]}
        recovered = {"id": "jra-2026-11-28-京都-09", "date": "2026-11-28",
                     "horses": [{"horseNumber": 1, "frameNumber": 1,
                                 "name": "甲", "jockey": "A"},
                                {"horseNumber": 2, "frameNumber": 2,
                                 "name": "乙", "jockey": "B"}]}
        grafted = prefetch._apply_recovered_identity(
            copy.deepcopy(current), copy.deepcopy(recovered))
        self.assertIsNotNone(grafted)
        by_name = {h["name"]: h for h in grafted["horses"]}
        self.assertEqual(by_name["甲"]["horseNumber"], 1)
        self.assertEqual(by_name["甲"]["bodyWeight"], 500)
        different = copy.deepcopy(recovered)
        different["horses"][1]["name"] = "丙"
        self.assertIsNone(prefetch._apply_recovered_identity(
            copy.deepcopy(current), different))


if __name__ == "__main__":
    unittest.main()
