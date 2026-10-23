import unittest
from unittest.mock import patch
from arvexq.research.margin_abcde_candidate import score, WEIGHTS

class MarginABCDETests(unittest.TestCase):
    def test_weights_sum(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.)

    def test_missing_margin_must_not_be_fabricated(self):
        runs=[{"finish":2,"fieldSize":10,"opponentLevel":.8,"distance":1400,
               "track":"園田","surface":"ダート","cornerPositions":[3,2]}]
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",return_value=runs):
            self.assertIsNone(score({},{"distance":1400,"track":"園田","surface":"ダート"}))

    def test_margin_participates_when_observed(self):
        def evidence(margin):
            return [{"marginSeconds":margin,"finish":2,"fieldSize":10,
                     "opponentLevel":.8,"distance":1400,"track":"園田",
                     "surface":"ダート","cornerPositions":[3,2]}]
        race={"distance":1400,"track":"園田","surface":"ダート"}
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",return_value=evidence(.2)):
            near=score({},race)
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",return_value=evidence(2.0)):
            far=score({},race)
        self.assertIsNotNone(near)
        self.assertGreater(near["score"], far["score"])
        self.assertIn("E",near["missing"])

    def test_passing_positions_are_used_without_new_source(self):
        run = {"marginSeconds": 0.2, "finish": 2, "fieldSize": 10,
               "distance": 1400, "track": "園田", "surface": "ダート",
               "passing": [7, 2]}
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",
                   return_value=[run]):
            result = score({}, {"distance": 1400, "track": "園田",
                                "surface": "ダート"})
        self.assertIsNotNone(result["factors"]["D"])
        self.assertGreater(result["factors"]["D"], 0.5)

    def test_hyphenated_passing_is_real_pace_evidence(self):
        run = {"marginSeconds": 0.2, "finish": 2, "fieldSize": 10,
               "distance": 1400, "track": "園田", "surface": "ダート",
               "passing": "7-4-2"}
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",
                   return_value=[run]):
            report = score({}, {"distance": 1400, "track": "園田",
                                "surface": "ダート"})
        self.assertIsNotNone(report["factors"]["D"])
        self.assertGreater(report["factors"]["D"], 0.5)

    def test_unknown_passing_is_not_synthetic_evidence(self):
        run = {"marginSeconds": 0.2, "finish": 2, "fieldSize": 10,
               "distance": 1400, "track": "園田", "surface": "ダート",
               "passing": "unknown"}
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",
                   return_value=[run]):
            report = score({}, {"distance": 1400, "track": "園田",
                                "surface": "ダート"})
        self.assertIsNone(report["factors"]["D"])

    def test_impossible_finish_not_used_as_opponent_or_suitability(self):
        run = {"marginSeconds": 0.4, "finish": 15, "fieldSize": 10,
               "opponentLevel": 0.8, "distance": 1400,
               "track": "園田", "surface": "ダート"}
        with patch("arvexq.research.margin_abcde_candidate.observed_runs",
                   return_value=[run]):
            result = score({}, {"distance": 1400, "track": "園田",
                                "surface": "ダート"})
        self.assertIsNone(result["factors"]["B"])
        self.assertIsNone(result["factors"]["C"])

if __name__ == "__main__":
    unittest.main()
