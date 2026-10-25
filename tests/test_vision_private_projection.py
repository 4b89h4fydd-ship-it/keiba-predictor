"""Public ARVEXQ API must never expose its internal race-video research store."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from arvexq.forecast.publication import public_race, RETIRED_KEYS

PRIVATE = (
    "visionResearch", "visionResearchHistory",
    "visionResearchAppliedToProductionPrediction",
    "visionResearchStatus", "visionResearchHistoricalRuns",
    "videoSha256", "modelSha256", "verifiedIdentityMap", "calibration",
)


def assert_private_absent(test, value):
    if isinstance(value, dict):
        test.assertFalse(set(value).intersection(PRIVATE))
        for v in value.values():
            assert_private_absent(test, v)
    if isinstance(value, list):
        for v in value:
            assert_private_absent(test, v)


class InternalVideoIsNeverPublished(TestCase):
    def test_recursive_internal_video_is_removed_without_mutating_original(self):
        source = {
            "id": "nar-2026-10-25-園田-01", "date": "2026-10-25",
            "visionResearchAppliedToProductionPrediction": False,
            "preparedMeta": {
                "visionResearchStatus": "internal-unvalidated-not-applied-to-marks",
                "visionResearchHistoricalRuns": 1,
                "cardComplete": True,
            },
            "horses": [{
                "horseNumber": 1, "name": "架空",
                "visionResearchHistory": [{
                    "raceId": "historical", "videoSha256": "a" * 64,
                    "distanceLossMeters": 25, "calibration": "survey"
                }],
                "recentRaces": [{
                    "date": "2026-10-22",
                    "visionResearch": {
                        "videoSha256": "a" * 64, "observedSpeedMps": 12.3,
                        "modelSha256": "b" * 64, "verifiedIdentityMap": {}
                    },
                    "finish": 2
                }],
            }],
            "status": "公開する一般レース情報",
        }
        original = deepcopy(source)
        with patch("arvexq.forecast.publication.build_prediction", return_value=None):
            response = public_race(source)
        assert_private_absent(self, response)
        self.assertEqual(response["horses"][0]["recentRaces"][0]["finish"], 2)
        self.assertEqual(response["preparedMeta"]["cardComplete"], True)
        self.assertEqual(source, original)
        self.assertEqual(response["predictionStatus"], "disabled")

    def test_all_private_keys_are_in_projection_filter(self):
        self.assertTrue(set(PRIVATE).issubset(RETIRED_KEYS))
