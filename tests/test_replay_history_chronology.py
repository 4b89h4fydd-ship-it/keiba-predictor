"""Regression: retrospective evaluation must not use target-day or future horse results."""
import unittest
from scripts.arvexq_current_prediction_audit import scrub_for_replay


class RetrospectiveReplayChronologyTests(unittest.TestCase):
    def test_removes_target_future_and_undated_runs(self):
        detail = {
            "id": "nar-2026-10-21-test-01",
            "result": {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]},
            "horses": [{"horseNumber": 1, "allPastRuns": [
                {"date": "2026-10-20", "finish": 5},
                {"date": "2026-10-21", "finish": 1},
                {"date": "2026-10-22", "finish": 2},
                {"finish": 3},
            ], "recentRaces": [
                {"raceDate": "2026-10-19", "finish": 2},
                {"raceDate": "2026-10-23", "finish": 1},
            ]}],
        }
        replay = scrub_for_replay(detail, "2026-10-21")
        self.assertNotIn("result", replay)
        self.assertEqual([r["date"] for r in replay["horses"][0]["allPastRuns"]], ["2026-10-20"])
        self.assertEqual([r["raceDate"] for r in replay["horses"][0]["recentRaces"]], ["2026-10-19"])
        self.assertEqual(len(detail["horses"][0]["allPastRuns"]), 4)


if __name__ == "__main__":
    unittest.main()
