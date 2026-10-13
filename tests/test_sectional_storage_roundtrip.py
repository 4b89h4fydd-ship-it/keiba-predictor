import unittest
from arvexq.ingest.career_transport import pack_horse,recover_horse
from arvexq.prediction.factor_model import collect_horse_raw_metrics

class SectionalStorageTests(unittest.TestCase):
    def test_preserve_observed_feed_fields(self):
        run={"date":"2026-10-10","finish":2,"fieldSize":10,"last3FRank":3,
             "last3FPercentile":0.7,"last3f":35.2,"margin":0.3}
        horse=pack_horse({"horseNumber":1,"recentRaces":[run]},"2026-10-14")
        compact=horse["recentRaces"][0]
        self.assertEqual(compact["last3FRank"],3)
        self.assertEqual(compact["last3FPercentile"],0.7)
        recovered=recover_horse(horse,"2026-10-14")
        self.assertEqual(recovered["recentRaces"][0]["last3FRank"],3)
        actual=collect_horse_raw_metrics(horse,{"date":"2026-10-14"})
        self.assertAlmostEqual(actual["sectional"],7/9)
    def test_unobserved_sectional_remains_unknown(self):
        horse=pack_horse({"horseNumber":1,"recentRaces":[
            {"date":"2026-10-10","finish":2,"fieldSize":10}
        ]},"2026-10-14")
        self.assertIsNone(collect_horse_raw_metrics(horse,{"date":"2026-10-14"})["sectional"])

if __name__=="__main__":
    unittest.main()
