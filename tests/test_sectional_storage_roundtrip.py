import unittest
from arvexq.ingest.career_transport import pack_horse,recover_horse
from arvexq.prediction.past_performance import observed_runs

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
        actual=observed_runs(horse,{"date":"2026-10-14"})[0]
        self.assertAlmostEqual(actual["last3fRank"],3)
    def test_unobserved_sectional_remains_unknown(self):
        horse=pack_horse({"horseNumber":1,"recentRaces":[
            {"date":"2026-10-10","finish":2,"fieldSize":10}
        ]},"2026-10-14")
        self.assertIsNone(observed_runs(horse,{"date":"2026-10-14"})[0]["last3fRank"])

if __name__=="__main__":
    unittest.main()
