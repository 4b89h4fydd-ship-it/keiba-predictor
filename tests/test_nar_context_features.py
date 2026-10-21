"""Regression for NAR-specific, strictly pre-off sourced contextual evidence."""
from __future__ import annotations

from copy import deepcopy
import unittest

from arvexq.prediction.nar_context_features import build_nar_context_features
from arvexq.prediction.mass_feature_factory import (
    FEATURE_SCHEMA_VERSION, build_horse_features, build_race_feature_matrix,
)
from arvexq.prediction.mass_feature_snapshot import build_mass_feature_snapshot
from arvexq.prediction.mass_feature_selection import snapshot_feature_allowed


def sample():
    race = {
        "id": "nar-2026-10-21-kochi-11", "circuit": "地方", "date": "2026-10-21",
        "track": "高知", "surface": "ダート", "condition": "重",
        "distance": 1400, "raceNumber": 11, "startTime": "20:50",
        "preRacePrediction": {"fixedAt": "2026-10-21T20:30:00+09:00"},
        "trackBiasEstimate": {
            "capturedAt": "2026-10-21T20:20:00+09:00",
            "observedThrough": "2026-10-21T20:00:00+09:00",
            "sourceKind": "preoff-historical-results", "sourceRef": "official-history:20261021-before-11",
            "sampleRaces": 7, "frontBackScore": 0.4,
            "insideOutsideScore": -0.2,
        },
    }
    horse = {
        "horseNumber": 1, "name": "検証馬", "jockey": "現騎手",
        "oddsHistory": [
            {"capturedAt": "2026-10-21T20:00:00+09:00", "winOdds": 8.0, "sourceKind": "official"},
            {"capturedAt": "2026-10-21T20:25:00+09:00", "winOdds": 4.0, "sourceKind": "official"},
            {"capturedAt": "2026-10-21T20:45:00+09:00", "winOdds": 1.3, "sourceKind": "official"},
        ],
        "recentRaces": [
            {
                "date": "2026-10-20", "track": "高知", "surface": "ダート",
                "condition": "重", "distance": 1400, "fieldSize": 10,
                "cornerPositions": [1, 1, 3, 6], "finish": 8, "jockey": "旧騎手",
                "early3FSeconds": 38.6, "sectionalProvenance": {
                    "sourceKind": "reviewed-video", "sourceRef": "official-race-video:20261020-8"},
                "tripObservations": {
                    "sourceKind": "reviewed-video", "sourceRef": "official-race-video:20261020-8",
                    "wideTrip": True, "kickback": False, "blocked": False, "slowStart": False,
                },
            },
            {
                "date": "2026-10-15", "track": "高知", "surface": "ダート",
                "condition": "重", "distance": 1400, "fieldSize": 10,
                "cornerPositions": [2, 2, 2, 3], "finish": 3, "jockey": "旧騎手",
                "first3FSeconds": 37.8, "sectionalProvenance": {
                    "sourceKind": "official", "sourceRef": "published:20261015-5"},
                "tripObservations": {
                    "sourceKind": "official-stewards", "sourceRef": "official:20261015-5",
                    "wideTrip": False, "kickback": True,
                },
            },
        ],
    }
    return race, horse


class NARContextFeatureTest(unittest.TestCase):
    def test_existing_mass_factory_and_frozen_snapshot_receive_nar_signals(self):
        race, horse = sample()
        original = deepcopy((race, horse))
        feats = build_horse_features(horse, race)
        self.assertEqual(feats["nar::pace::front_rate_w5"], 1.0)
        self.assertEqual(feats["nar::pace::front_fade_rate_w5"], 0.5)
        self.assertAlmostEqual(feats["nar::sectional::comparable_race_first3f_median_w5"], 38.2)
        self.assertEqual(feats["nar::sectional::comparable_race_sample_w5"], 2)
        self.assertEqual(feats["nar::trip::wideTrip_rate_w5"], 0.5)
        self.assertEqual(feats["nar::trip::kickback_rate_w5"], 0.5)
        self.assertEqual(feats["nar::jockey::changed_from_previous"], 1)
        self.assertEqual(feats["nar::bias::sample_races"], 7)
        self.assertAlmostEqual(feats["nar::bias::front_back_score"], 0.4)
        self.assertAlmostEqual(feats["market::preoff_odds_change_ratio"], -0.5)
        self.assertEqual(feats["market::preoff_odds_observations"], 2)
        self.assertTrue(snapshot_feature_allowed("nar::trip::wideTrip_rate_w5"))
        self.assertTrue(snapshot_feature_allowed("relative::nar::pace::front_rate_w5::percentile"))
        self.assertIn("nar-provenanced-context", FEATURE_SCHEMA_VERSION)
        snap = build_mass_feature_snapshot({**race, "horses": [horse]})
        self.assertIn("nar::pace::front_rate_w5", snap["rows"][0]["features"])
        self.assertEqual(snap["schemaVersion"], FEATURE_SCHEMA_VERSION)
        self.assertEqual((race, horse), original, "source records cannot be modified")
        self.assertEqual(snap["featureHash"], build_mass_feature_snapshot({**race, "horses": [horse]})["featureHash"])

    def test_nar_only_and_no_banei_crossover(self):
        race, horse = sample()
        for circuit, track in [("中央", "高知"), ("JRA", "東京"), ("地方", "帯広")]:
            with self.subTest(circuit=circuit, track=track):
                alternate = {**race, "circuit": circuit, "track": track}
                self.assertEqual(build_nar_context_features(horse, alternate, horse["recentRaces"]), {})
                self.assertFalse(any(x.startswith("nar::") for x in build_horse_features(horse, alternate)))

    def test_no_same_day_future_or_unproven_race_lap(self):
        race, horse = sample()
        horse["recentRaces"].insert(0, {
            "date": "2026-10-22", "track": "高知", "distance": 1400,
            "surface": "ダート", "condition": "重", "fieldSize": 10,
            "cornerPositions": [1], "finish": 1,
            "first3FSeconds": 20.0, "sectionalProvenance": {
                "sourceKind": "official", "sourceRef": "future"},
        })
        horse["recentRaces"].append({
            "date": "2026-10-10", "track": "高知", "distance": 1400,
            "surface": "ダート", "condition": "重", "fieldSize": 10,
            "cornerPositions": [4], "finish": 4,
            "first3FSeconds": 29.1,  # no source -> absent
        })
        features = build_horse_features(horse, race)
        self.assertEqual(features["nar::sectional::comparable_race_sample_w5"], 2)
        self.assertAlmostEqual(features["nar::sectional::comparable_race_first3f_median_w5"], 38.2)
        with_result = {**race, "result": {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}}
        self.assertEqual(features, build_horse_features(horse, with_result))

    def test_cross_distance_and_going_do_not_share_raw_sectionals(self):
        race, horse = sample()
        changed = {**race, "distance": 1000, "condition": "良"}
        feats = build_horse_features(horse, changed)
        self.assertFalse(any(k.startswith("nar::sectional") for k in feats))
        self.assertIn("nar::pace::front_rate_w5", feats)

    def test_unverified_bias_trip_and_postoff_odds_fail_closed(self):
        race, horse = sample()
        race["trackBiasEstimate"]["capturedAt"] = "2026-10-21T21:10:00+09:00"
        for run in horse["recentRaces"]:
            run["tripObservations"]["sourceRef"] = ""
            run["sectionalProvenance"]["sourceRef"] = ""
        horse["oddsHistory"] = [
            {"capturedAt": "2026-10-21T20:40:00+09:00", "winOdds": 2.0, "sourceKind": "official"},
            {"capturedAt": "2026-10-21T20:50:00+09:00", "winOdds": 1.1, "sourceKind": "official"},
        ]
        result = build_horse_features(horse, race)
        self.assertFalse(any(k.startswith(("nar::bias::", "nar::trip::", "nar::sectional::")) for k in result))
        self.assertNotIn("market::preoff_odds_change_ratio", result)
        race["preRacePrediction"].pop("fixedAt")
        self.assertNotIn("market::preoff_odds_change_ratio", build_horse_features(horse, race))

    def test_missing_history_does_not_fabricate_pace_or_track_bias(self):
        race, horse = sample()
        race.pop("trackBiasEstimate")
        horse["recentRaces"] = []
        features = build_horse_features(horse, race)
        self.assertFalse(any(k.startswith("nar::pace::") for k in features))
        self.assertFalse(any(k.startswith("nar::bias::") for k in features))

    def test_relative_nar_context_is_isolated_from_jra(self):
        race, horse = sample()
        other = deepcopy(horse)
        other["horseNumber"] = 2
        other["recentRaces"][0]["cornerPositions"] = [9, 9, 9, 9]
        rows = build_race_feature_matrix([horse, other], race)
        self.assertTrue(any(k.startswith("relative::nar::pace") for k in rows[0]["features"]))
        jra = build_race_feature_matrix([horse, other], {**race, "circuit": "中央"})
        self.assertFalse(any("nar::" in k for row in jra for k in row["features"]))


if __name__ == "__main__":
    unittest.main()
