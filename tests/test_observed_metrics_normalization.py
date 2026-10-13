import unittest
from arvexq.history import normalize_run
from arvexq.prediction.factor_model import collect_horse_raw_metrics
from arvexq.prediction.past_performance import analyze_past_performance

class ObservedMetricsTests(unittest.TestCase):
    def test_sectional_rank_survives_history_normalization(self):
        run={"date":"2026-10-10","finish":3,"fieldSize":10,"上がり順位":2,"着差":0.2}
        row=normalize_run(run)
        self.assertEqual(row["last3fRank"],2)
        self.assertEqual(row["margin"],0.2)
        horse={"horseNumber":1,"recentRaces":[run]}
        race={"date":"2026-10-14"}
        raw = collect_horse_raw_metrics(horse,race)
        self.assertAlmostEqual(raw["recentForm"],7/9)
        self.assertNotIn("sectional",raw)
        self.assertEqual(analyze_past_performance(horse,race)["marginObservedRuns"],1)

    def test_no_sectional_fabricated_when_missing(self):
        horse={"horseNumber":1,"recentRaces":[{"date":"2026-10-10","finish":3,"fieldSize":10,"last3f":36.1}]}
        raw = collect_horse_raw_metrics(horse,{"date":"2026-10-14"})
        self.assertAlmostEqual(raw["recentForm"],7/9)
        self.assertNotIn("sectional",raw)

if __name__=="__main__":
    unittest.main()
