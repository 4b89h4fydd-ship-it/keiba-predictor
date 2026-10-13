import unittest
from arvexq.ingest.fallback_enrichment import _observed_sectional_rank_count

class SectionalPrefetchTests(unittest.TestCase):
    def test_measured_position_count(self):
        h={"recentRaces":[
            {"date":"2026-10-09","finish":2,"fieldSize":12,"last3FRank":3},
            {"date":"2026-10-08","finish":1,"fieldSize":9,"last3fRank":1},
            {"date":"2026-10-07","finish":2,"fieldSize":8,"last3fRank":99},
            {"date":"2026-10-16","finish":1,"fieldSize":12,"last3fRank":1}]}
        self.assertEqual(_observed_sectional_rank_count(h,"2026-10-14"),2)
    def test_missing_timing_never_counts_as_rank(self):
        h={"recentRaces":[{"date":"2026-10-08","finish":1,"fieldSize":9,"last3f":34.5}]}
        self.assertEqual(_observed_sectional_rank_count(h,"2026-10-14"),0)

if __name__=="__main__":
    unittest.main()
