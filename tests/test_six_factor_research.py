"""Six-factor audit tests, including exact course and missing-evidence cases."""
import unittest
from unittest.mock import patch
from arvexq.prediction.six_factor_research import signals

RACE = {"date":"2026-10-16","track":"京都","surface":"芝","distance":1600,"direction":"右"}
def run(**kw):
    return {**{"date":"2026-10-01","track":"京都","surface":"芝","distance":1600,"direction":"右",
            "finish":2,"fieldSize":10,"marginSeconds":0.2,"cornerPositions":"5-4-3"},**kw}

class SixFactorTests(unittest.TestCase):
    def score(self, rows, race=None):
        with patch("arvexq.prediction.six_factor_research.observed_runs",return_value=rows):
            return signals({},race or RACE)

    def test_exact_course(self):
        a=self.score([run()])
        self.assertEqual(a["exactCourseStarts"],1)
        self.assertEqual(a["exactCourseTop3Rate"],1)
        self.assertAlmostEqual(a["exactCourseMeanMarginSeconds"],.2)
    def test_opposite_direction_excluded(self):
        self.assertEqual(self.score([run(direction="左")])["exactCourseStarts"],0)
    def test_different_distance_excluded(self):
        self.assertEqual(self.score([run(distance=1800)])["exactCourseStarts"],0)
    def test_different_track_excluded(self):
        self.assertEqual(self.score([run(track="東京")])["exactCourseStarts"],0)
    def test_no_unknown_direction_match(self):
        self.assertEqual(self.score([run()],{**RACE,"direction":None})["exactCourseStarts"],0)
    def test_zero_margin_is_observed(self):
        self.assertEqual(self.score([run(marginSeconds=0)])["exactCourseMeanMarginSeconds"],0)
    def test_no_margin_is_missing_not_zero(self):
        a=self.score([run(marginSeconds=None)])
        self.assertIsNone(a["exactCourseMeanMarginSeconds"])
        self.assertEqual(a["marginSamples"],0)
    def test_top3_full_history_and_recent(self):
        a=self.score([run(finish=5),run(finish=2),run(finish=1)])
        self.assertAlmostEqual(a["overallTop3Rate"],2/3)
        self.assertAlmostEqual(a["recentWeightedTop3Rate"],(2+1)/6)
    def test_corner_gain(self):
        self.assertAlmostEqual(self.score([run()])["recentCornerToFinishGain"],(3-2)/9)

if __name__=="__main__":
    unittest.main()
