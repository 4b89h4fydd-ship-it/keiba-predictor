import copy
import unittest

from arvexq.pipeline.fingerprints import analysis_input_hash


class PredictionFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.race = {
            "id": "jra-2026-10-14-test-01",
            "track": "東京", "surface": "芝", "distance": 1600,
            "weather": "晴", "condition": "良",
            "horses": [
                {"horseNumber": 1, "name": "A", "recentRaces": [{"date": "2026-09-01", "finish": 2}]},
                {"horseNumber": 2, "name": "B", "recentRaces": [{"date": "2026-09-01", "finish": 4}]},
            ],
        }

    def test_model_outputs_do_not_change_input_fingerprint(self):
        changed = copy.deepcopy(self.race)
        changed["horses"][0]["integratedEvaluation"] = {"score": 90, "mark": "◎"}
        self.assertEqual(analysis_input_hash(self.race), analysis_input_hash(changed))

    def test_new_recent_race_changes_input_fingerprint(self):
        changed = copy.deepcopy(self.race)
        changed["horses"][0]["recentRaces"][0]["finish"] = 1
        self.assertNotEqual(analysis_input_hash(self.race), analysis_input_hash(changed))

    def test_weather_change_changes_input_fingerprint(self):
        changed = copy.deepcopy(self.race)
        changed["weather"] = "雨"
        self.assertNotEqual(analysis_input_hash(self.race), analysis_input_hash(changed))


if __name__ == "__main__":
    unittest.main()
