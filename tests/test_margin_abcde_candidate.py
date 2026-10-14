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

if __name__ == "__main__":
    unittest.main()
