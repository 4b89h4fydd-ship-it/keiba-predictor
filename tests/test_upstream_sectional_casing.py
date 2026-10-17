import unittest
from arvexq.history import normalize_run
from arvexq.prediction.past_performance import observed_runs

class UpstreamCaseTests(unittest.TestCase):
    def test_jra_source_field_aliases(self):
        r={"date":"2026-10-10","finish":2,"fieldSize":9,"last3FRank":3,"last3FPercentile":0.8}
        n=normalize_run(r)
        self.assertEqual(n["last3fRank"],3)
        self.assertEqual(n["last3fPercentile"],0.8)
        h={"horseNumber":1,"recentRaces":[r]}
        self.assertAlmostEqual(observed_runs(h,{"date":"2026-10-14"})[0]["last3fRank"],3)
    def test_unobserved_still_unknown(self):
        r={"date":"2026-10-10","finish":2,"fieldSize":9}
        self.assertIsNone(normalize_run(r)["last3fRank"])

if __name__=="__main__":
    unittest.main()
