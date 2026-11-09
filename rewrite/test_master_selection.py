"""Full card selection and cautious risk labels."""
import unittest

from rewrite.analysis.master_selection import select_daily_races


def card(rid, *, market="complete", unknown=None, gap=True, danger=False):
    values = [0.8, 0.75, 0.5 if gap else 0.73, 0.45, 0.4]
    return {
        "raceId": rid,
        "masterAnalysis": {
            "status": "shadow-candidate", "marketStatus": market,
            "pace": {"unknown": unknown or []},
            "runners": [
                {"horseNumber": i + 1, "coveragePoints": 84,
                 "pTop3": p,
                 "popularRisk": "C-candidate" if danger and i == 1 else "A-candidate"}
                for i, p in enumerate(values)
            ],
        },
    }


class SelectionTests(unittest.TestCase):
    def test_full_card_shortlist_not_fixed_36(self):
        pool = [card(f"r{i}") for i in range(36)]
        result = select_daily_races(pool)
        self.assertEqual(result["inputRaces"], 36)
        self.assertEqual(result["selectedCount"], 36)
        self.assertEqual(result["selected"][0]["headCandidates"], [1, 2])
        self.assertEqual(result["status"], "research-only-not-purchase-advice")

    def test_unknown_odds_and_ambiguous_two_head_are_not_selected(self):
        pool = [card("r1", market="unavailable"), card("r2", gap=False),
                card("r3", unknown=[4]), card("r4", danger=True)]
        result = select_daily_races(pool)
        self.assertEqual(result["selectedCount"], 0)
        self.assertTrue(all(not r["selected"] for r in result["allDecisions"]))
        self.assertEqual(result["allDecisions"][3]["avoidHypotheses"], [2])

    def test_duplicate_not_double_counted(self):
        result = select_daily_races([card("same"), card("same")])
        self.assertEqual(result["evaluatedRaces"], 1)


if __name__ == "__main__":
    unittest.main()
