from __future__ import annotations
import unittest
from arvexq.prediction.career_evidence import career_rates


class CareerEvidenceTests(unittest.TestCase):
    def test_all_historical_runs_not_last_five_and_no_future_leakage(self):
        history = [{"date": f"2026-0{month}-01", "raceId": f"r{month}",
                    "fieldSize": 10, "finish": 1 if month <= 3 else 4}
                   for month in range(1, 9)]
        history.append({"date": "2026-10-12", "raceId": "future", "fieldSize": 10, "finish": 1})
        horse = {"allPastRuns": history, "recentRaces": history[-5:]}
        a = career_rates(horse, "2026-10-09")
        self.assertEqual(a["datedStarts"], 8)
        self.assertEqual(a["wins"], 3)
        self.assertEqual(a["top2Rate"], 3 / 8)
        self.assertEqual(a["top3Rate"], 3 / 8)

    def test_unknown_history_not_assumed_zero_career_success(self):
        a = career_rates({"recentRaces": [{"finish": 1, "fieldSize": 10}]}, "2026-10-09")
        self.assertIsNone(a["winRate"])
        self.assertEqual(a["status"], "missing-full-dated-history")

    def test_same_day_and_duplicate_runs_not_counted(self):
        rows = [{"date": "2026-10-08", "raceId": "x", "fieldSize": 10, "finish": 2},
                {"date": "2026-10-08", "raceId": "x", "fieldSize": 10, "finish": 2},
                {"date": "2026-10-09", "raceId": "y", "fieldSize": 10, "finish": 1}]
        a = career_rates({"allPastRuns": rows}, "2026-10-09")
        self.assertEqual(a["datedStarts"], 1)
        self.assertEqual(a["top2"], 1)

if __name__ == "__main__":
    unittest.main()
