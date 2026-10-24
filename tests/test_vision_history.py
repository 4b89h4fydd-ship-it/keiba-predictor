"""No-outcome-leakage guarantees for internal video-only research feature joins."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from arvexq.vision.history import (
    attach_from_store, attach_historical_video, compact_video_evidence,
    evidence_filename, load_evidence, write_evidence,
)


def vision_report():
    return {
        "version": "arvexq-video-detector-v1",
        "predictionApplied": False,
        "manifest": {
            "raceId": "nar-2026-10-15-園田-02", "raceDate": "2026-10-15",
            "source": {"rightsVerified": True, "calibrationVerified": True,
                       "coordinateSystem": "ground-plane-meters",
                       "sha256": "a" * 64},
            "model": {"weightsSha256": "b" * 64},
            "frames": [{"horses": [
                {"horseNumber": 1, "identitySource": "automated-ocr-provisional"}
            ]}],
        },
        "measurements": {
            "videoSha256": "a" * 64, "evidenceHash": "c" * 64,
            "analysisStatus": "tracking-measurements-not-a-validated-video-model",
            "runners": [
                {"horseNumber": 1, "coverage": .75, "validMovementSegments": 20,
                 "averageObservedSpeedMps": 16.4, "observedPathMeters": 1250,
                 "distanceLossMeters": None, "possibleSlowdowns": [{"timeSeconds": 20.}],
                 "observationStatus": "observed"}
            ]
        },
    }


def configuration():
    return {"raceId": "nar-2026-10-15-園田-02", "raceDate": "2026-10-15",
            "track": "園田", "raceNumber": 2,
            "horseIdentityByNumber": {"1": "stable-123"}}


def future_card(day="2026-10-25", stable_id="stable-123"):
    return {"id": "nar-2026-10-25-園田-01", "date": day, "track": "園田",
            "horses": [{"id": stable_id, "horseNumber": 4, "name": "Example",
                        "recentRaces": [{"date": "2026-10-15", "track": "園田",
                                         "raceNumber": 2,
                                         "raceId": "nar-2026-10-15-園田-02",
                                         "finish": 9}]}]}


class VideoHistoryTests(TestCase):
    def test_compact_evidence_keeps_uncertainty_and_no_video(self):
        compact = compact_video_evidence(vision_report(), configuration())
        self.assertEqual(compact["runners"]["1"]["horseId"], "stable-123")
        self.assertEqual(compact["runners"]["1"]["identitySource"],
                         "automated-ocr-provisional")
        self.assertEqual(compact["runners"]["1"]["possibleSlowdownEvents"], 1)
        self.assertFalse(compact["predictionApplied"])
        self.assertFalse(compact["verifiedForecastImprovement"])
        self.assertNotIn("frames", compact)

    def test_future_joins_matching_horse_and_race_not_result(self):
        evidence = compact_video_evidence(vision_report(), configuration())
        card = future_card()
        original = deepcopy(card)
        enriched = attach_historical_video(card, [evidence])
        self.assertEqual(card, original)
        vision = enriched["horses"][0]["recentRaces"][0]["visionResearch"]
        self.assertEqual(vision["trackingCoverage"], .75)
        self.assertIsNone(vision["distanceLossMeters"])
        self.assertTrue(vision["researchOnly"])
        self.assertFalse(enriched["visionResearchAppliedToProductionPrediction"])

    def test_reused_saddlecloth_number_is_not_horse_identity(self):
        evidence = compact_video_evidence(vision_report(), configuration())
        result = attach_historical_video(future_card(stable_id="different"), [evidence])
        self.assertNotIn("visionResearch", result["horses"][0]["recentRaces"][0])

    def test_no_future_video_or_race_mismatch(self):
        evidence = compact_video_evidence(vision_report(), configuration())
        current = future_card(day="2026-10-15")
        result = attach_historical_video(current, [evidence])
        self.assertNotIn("visionResearch", result["horses"][0]["recentRaces"][0])
        wrong_track = future_card()
        wrong_track["horses"][0]["recentRaces"][0]["track"] = "浦和"
        self.assertNotIn("visionResearch", attach_historical_video(
            wrong_track, [evidence])["horses"][0]["recentRaces"][0])

    def test_immutable_local_store_and_no_raw_video(self):
        evidence = compact_video_evidence(vision_report(), configuration())
        with TemporaryDirectory() as tmp:
            first = write_evidence(tmp, evidence)
            self.assertEqual(first, write_evidence(tmp, evidence))
            self.assertEqual(load_evidence(tmp, evidence["raceId"]), evidence)
            self.assertEqual(attach_from_store(future_card(), tmp)["horses"][0][
                "recentRaces"][0]["visionResearch"]["horseNumber"], 1)
            altered = deepcopy(evidence)
            altered["runners"]["1"]["coverage"] = .1
            with self.assertRaisesRegex(ValueError, "immutable"):
                write_evidence(tmp, altered)
            self.assertTrue(first.name.endswith(".json"))
            self.assertNotIn("園田", first.name)

    def test_reject_forged_source(self):
        false_source = vision_report()
        false_source["manifest"]["source"]["rightsVerified"] = False
        with self.assertRaisesRegex(ValueError, "source"):
            compact_video_evidence(false_source, configuration())
