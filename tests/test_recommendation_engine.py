import unittest

from arvexq.prediction.recommendation_engine import (
    evaluate_tickets, rank_marks, recommend,
)


class RecommendationEngineTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = [
            (("1", "2", "3", "4"), 0.6),
            (("2", "1", "4", "3"), 0.3),
            (("4", "3", "2", "1"), 0.1),
        ]

    def test_probabilities_and_marks(self):
        result = rank_marks(self.scenarios)
        self.assertEqual(result["marks"]["1"], "◎")
        self.assertAlmostEqual(result["win"]["1"], 0.6)
        self.assertAlmostEqual(sum(result["win"].values()), 1.0)

    def test_exact_joint_ticket_probabilities(self):
        odds = {("exacta", ("1", "2")): 4,
                ("quinella", ("1", "2")): 2,
                ("trifecta", ("1", "2", "3")): 10}
        by_type = {t.kind: t for t in evaluate_tickets(self.scenarios, odds)}
        self.assertAlmostEqual(by_type["exacta"].win_probability, 0.6)
        self.assertAlmostEqual(by_type["quinella"].win_probability, 0.9)
        self.assertAlmostEqual(by_type["trifecta"].win_probability, 0.6)

    def test_refuses_unattainable_joint_hit_target(self):
        odds = {("win", ("1",)): 4}
        result = recommend(self.scenarios, odds, min_hit_probability=0.8)
        self.assertEqual(result["status"], "no_recommendation")

    def test_recommends_when_constraints_satisfied(self):
        odds = {("win", ("1",)): 2.5, ("win", ("2",)): 5}
        result = recommend(self.scenarios, odds, min_hit_probability=0.8)
        self.assertEqual(result["status"], "recommended")
        self.assertAlmostEqual(result["hit_probability"], 0.9)
        self.assertGreaterEqual(result["expected_return"], 1.0)

    def test_rejects_invalid_scenario_distribution(self):
        with self.assertRaises(ValueError):
            rank_marks([(("1", "2", "3"), 0.4)])
        with self.assertRaises(ValueError):
            rank_marks([(("1", "2", "3"), 0.5), (("1", "2", "4"), 0.5)])

    def test_missing_odds_produces_no_proposal(self):
        self.assertEqual(recommend(self.scenarios, {})["status"], "no_recommendation")


if __name__ == "__main__":
    unittest.main()
