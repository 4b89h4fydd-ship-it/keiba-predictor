import unittest
from arvexq.prediction.experimental_21_factor import AXES, historical, scored

class Experimental21FactorTests(unittest.TestCase):
    def test_all_axes_are_100_percent(self):
        self.assertEqual(set(AXES), {"true_run","pure","sectional"})
        self.assertAlmostEqual(sum(x[0] for x in AXES.values()),1.0)
        for _, signals in AXES.values():
            self.assertEqual(len(signals),7)
            self.assertAlmostEqual(sum(w for _,w in signals),1.0)
    def test_future_result_excluded(self):
        race={"date":"2026-10-13","track":"園田","distance":1400}
        h={"horseNumber":1,"recentRaces":[
            {"date":"2026-10-13","finish":1,"fieldSize":10},
            {"date":"2026-10-14","finish":1,"fieldSize":10},
            {"date":"2026-10-10","finish":7,"fieldSize":10}]}
        self.assertEqual(len(historical(h,race)),1)
    def test_missing_evidence_cannot_create_score(self):
        race={"date":"2026-10-13","track":"園田","distance":1400}
        h={"horseNumber":1,"recentRaces":[
            {"date":"2026-10-10","finish":1,"fieldSize":10}]}
        r=scored(h,race)
        self.assertIsNone(r["score"])
        self.assertEqual(r["status"],"insufficient-evidence")
        self.assertTrue(r["notCalibrated"])
    def test_no_race_date_no_evaluation(self):
        h={"horseNumber":1,"recentRaces":[{"date":"2026-10-11","finish":1,"fieldSize":10}]}
        self.assertEqual(historical(h,{}),[])

if __name__=="__main__":
    unittest.main()
