"""Independent safeguards for buyer-facing ARVEXQ research outputs."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from datetime import datetime, timezone
from unittest import TestCase

from arvexq.vision.observations import analyze_tracking
from arvexq.verification.trust_report import build_trust_report


def manifest():
    sha = "a" * 64
    return {
        "raceId": "nar-2026-10-21-園田-01", "raceDate": "2026-10-21",
        "source": {"sha256": sha, "rightsVerified": True,
                   "calibrationVerified": True, "coordinateSystem": "ground-plane-meters"},
        "referencePathMetersByHorse": {"1": 9.0, "2": 11.0},
        "frames": [
            {"timeSeconds": 0, "cameraId": "wide", "horses": [
                {"horseNumber": 1, "xMeters": 0, "yMeters": 0, "identityConfidence": .95, "visible": True},
                {"horseNumber": 2, "xMeters": 0, "yMeters": 1, "identityConfidence": .95, "visible": True}]},
            {"timeSeconds": 1, "cameraId": "wide", "horses": [
                {"horseNumber": 1, "xMeters": 5, "yMeters": 0, "identityConfidence": .95, "visible": True},
                {"horseNumber": 2, "xMeters": 5, "yMeters": 1, "identityConfidence": .95, "visible": True}]},
            {"timeSeconds": 2, "cameraId": "wide", "horses": [
                {"horseNumber": 1, "xMeters": 10, "yMeters": 0, "identityConfidence": .95, "visible": True},
                {"horseNumber": 2, "xMeters": 10, "yMeters": 1, "identityConfidence": .95, "visible": True}]},
        ],
    }


def settled(race_id="nar-test-1", finish=(1, 2, 3), payout=1580):
    race_date = "2026-10-01"
    captured = int(datetime(2026, 10, 1, 11, 55, tzinfo=timezone.utc).timestamp())
    # 12:30 JST = 03:30 UTC; captured time must be before scheduled post.
    captured = int(datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc).timestamp())
    lock = {"raceId": race_id, "raceDate": race_date, "capturedAtEpoch": captured,
            "frozen": True, "freezePolicy": "arvexq-server-prerace-seal-v1",
            "sealedAtEpoch": captured + 60,
            "horses": [{"horseNumber": 1, "mark": "◎"},
                       {"horseNumber": 2, "mark": "○"},
                       {"horseNumber": 3, "mark": "▲"}]}
    payload = {"raceId": race_id, "date": race_date,
               "captured": captured, "sealed": lock["sealedAtEpoch"],
               "horses": lock["horses"]}
    lock["sealRevision"] = sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), default=str).encode()).hexdigest()
    return {"id": race_id, "date": race_date, "startTime": "12:30",
            "circuit": "地方", "preRacePrediction": lock,
            "preRaceBet": {"items": [{"kind": "3連単", "combos": [[1, 2, 3]]}]},
            "result": {"status": "確定", "finishers": [
                {"horseNumber": no, "finish": pos + 1} for pos, no in enumerate(finish)],
                "payouts": [{"type": "3連単",
                             "combination": "-".join(map(str, finish)),
                             "amount": payout}]}}


class VisionEvidenceTests(TestCase):
    def test_distance_only_from_full_calibrated_tracking(self):
        data = analyze_tracking(manifest(), [1, 2])
        self.assertEqual(len(data["runners"]), 2)
        self.assertEqual(data["runners"][0]["distanceLossMeters"], 1.0)
        self.assertEqual(data["runners"][0]["observedPathMeters"], 10.0)
        self.assertEqual(data["analysisStatus"],
                         "tracking-measurements-not-a-validated-video-model")

    def test_occlusion_and_camera_cut_do_not_invent_distance(self):
        source = manifest()
        source["frames"][1]["horses"] = source["frames"][1]["horses"][:1]
        source["frames"][2]["cameraId"] = "finish"
        result = analyze_tracking(source, [1, 2])
        self.assertIsNone(result["runners"][0]["distanceLossMeters"])
        self.assertIsNone(result["runners"][1]["distanceLossMeters"])
        self.assertEqual(result["runners"][1]["coverage"], .6667)

    def test_refuse_unverified_source_and_duplicate_horses(self):
        source = manifest()
        source["source"]["rightsVerified"] = False
        with self.assertRaisesRegex(ValueError, "provenance"):
            analyze_tracking(source, [1, 2])
        source = manifest()
        source["frames"][0]["horses"].append(deepcopy(source["frames"][0]["horses"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze_tracking(source, [1, 2])


class HonestHistoryTests(TestCase):
    def test_all_wins_and_losses_are_counted(self):
        report = build_trust_report([settled("r1"), settled("r2", (2, 3, 1))])
        self.assertEqual(report["population"]["withVerifiedOriginalAndOfficialFinal"], 2)
        self.assertEqual(report["honmei"]["wins"], 1)
        self.assertEqual(report["honmei"]["top3Hits"], 2)
        self.assertEqual(report["honmei"]["winRate"], .5)
        self.assertEqual(report["ticketMetrics"]["byKind"]["3連単"]["sampleRaces"], 2)
        self.assertEqual(report["ticketMetrics"]["byKind"]["3連単"]["flatStakeReturnRate"], 7.9)
        self.assertFalse(report["verifiedProfitClaim"])

    def test_missing_original_visible_but_excluded(self):
        missing = settled("missing")
        missing.pop("preRacePrediction")
        report = build_trust_report([missing, settled("r1")])
        self.assertEqual(report["population"]["suppliedRaces"], 2)
        self.assertEqual(report["population"]["missingOrInvalidOriginal"], 1)
        self.assertEqual(report["everyRace"][0]["status"], "missing-preoff-original")

    def test_missing_official_payout_is_not_zero(self):
        bad = settled("r1")
        bad["result"]["payouts"] = []
        report = build_trust_report([bad])
        self.assertFalse(report["ticketMetrics"]["byKind"]["3連単"]["completePayouts"])
        self.assertIsNone(report["ticketMetrics"]["byKind"]["3連単"]["flatStakeReturnRate"])

    def test_modified_original_hash_is_rejected(self):
        tampered = settled("r1")
        tampered["preRacePrediction"]["horses"][0]["mark"] = "○"
        report = build_trust_report([tampered])
        self.assertEqual(report["population"]["withVerifiedOriginalAndOfficialFinal"], 0)
        self.assertEqual(report["population"]["missingOrInvalidOriginal"], 1)

    def test_no_retroactive_capture_and_duplicate_races(self):
        late = settled("r1")
        late["preRacePrediction"]["capturedAtEpoch"] += 86400
        report = build_trust_report([late])
        self.assertEqual(report["population"]["withVerifiedOriginalAndOfficialFinal"], 0)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_trust_report([settled("same"), settled("same")])
