"""JRA official history must not silently truncate a career at five."""
import unittest
from arvexq.ingest.jra_career_merge import merge_full_profile_history


class JraCareerMergeTests(unittest.TestCase):
    def test_twelve_observed_runs_keep_all_twelve(self):
        runs=[{"date":f"2026-{month:02d}-01","finish":month%5+1}
              for month in range(1,11)]
        runs += [{"date":"2025-10-01","finish":2},
                 {"date":"2025-11-01","finish":3}]
        horse={"name":"候補馬","recentRaces":runs[-5:]}
        result=merge_full_profile_history(horse,runs,"2026-10-11")
        self.assertEqual(len(result["allPastRuns"]),12)
        self.assertEqual(len(result["recentRaces"]),5)
        self.assertEqual(result["allPastRuns"][0]["date"],"2026-10-01")
        self.assertEqual(len(horse["recentRaces"]),5)
    def test_future_and_target_races_are_excluded(self):
        original={"name":"sample","recentRaces":[{"date":"2026-09-01","finish":1}]}
        added=[{"date":"2026-10-11","finish":1},
               {"date":"2026-11-01","finish":2},
               {"date":"2026-08-01","finish":3}]
        result=merge_full_profile_history(original,added,"2026-10-11")
        self.assertEqual([x["date"] for x in result["allPastRuns"]],
                         ["2026-09-01","2026-08-01"])
    def test_empty_source_does_not_discard_original_evidence(self):
        original={"name":"sample","allPastRuns":[{"date":"2026-03-01","finish":2}],
                  "recentRaces":[{"date":"2026-09-01","finish":1}]}
        result=merge_full_profile_history(original,[],"2026-10-11")
        self.assertEqual(len(result["allPastRuns"]),2)


if __name__=="__main__":
    unittest.main()
