"""Verify the unified 45/35/20 ranking without using the retired four-pillar gate."""
import unittest
from unittest.mock import patch

from arvexq.prediction.factor_model import MODEL_VERSION, PRIMARY_PILLARS, rank_factor_model
from arvexq.prediction.final_marks import apply_core_marks


class UnifiedThreeFactorTests(unittest.TestCase):
    def setUp(self):
        self.race = {"date": "2026-10-13", "circuit": "地方", "track": "園田",
                     "distance": 1400, "surface": "ダート", "horses": []}
        for num, true_run, pure, sectional in [
            (1, .90, .70, .70), (2, .65, .90, .70), (3, .60, .60, .70),
            (4, .45, .50, .40), (5, .40, .40, .30),
        ]:
            self.race["horses"].append({
                "horseNumber": num, "name": f"Horse{num}",
                "integratedEvaluation": {"v218Audit": {
                    "trueRun": true_run, "pure": pure, "sectional": sectional}},
            })

    def test_weights_and_single_ranking(self):
        ranking = rank_factor_model(self.race["horses"], self.race)
        self.assertEqual(PRIMARY_PILLARS, ("trueRun", "pure", "sectional"))
        self.assertIn("45-35-20", MODEL_VERSION)
        self.assertEqual(ranking[0]["horse"]["horseNumber"], 1)
        self.assertAlmostEqual(ranking[0]["score"], .45*.90+.35*.70+.20*.70)
        self.assertAlmostEqual(ranking[1]["score"], .45*.65+.35*.90+.20*.70)
        self.assertEqual(ranking[0]["primaryPillarCoverage"], 3)
        self.assertNotIn("ability", ranking[0]["pillarScores"])
        self.assertNotIn("pace", ranking[0]["pillarScores"])

    def test_marks_derive_from_the_exact_same_order(self):
        def ready(detail):
            detail["careerReadiness"] = {"ready": True, "activeHorses": 5,
                                          "completeHorses": 5}
            return detail

        with patch("arvexq.prediction.final_marks.attach_career_readiness",
                   side_effect=ready):
            detail = apply_core_marks(self.race)
        ordered = sorted(detail["horses"], key=lambda h: h["integratedEvaluation"]["rank"])
        self.assertEqual([h["integratedEvaluation"]["mark"] for h in ordered],
                         ["◎", "○", "▲", "△", "☆"])
        self.assertEqual(detail["honmeiDecision"]["horseNumber"],
                         ordered[0]["horseNumber"])
        self.assertEqual(sum(h["integratedEvaluation"]["mark"] == "◎"
                             for h in ordered), 1)
        self.assertNotIn("multiHeadSummary", detail)

    def test_all_missing_does_not_manufacture_ranking(self):
        self.race["horses"] = [
            {"horseNumber": 1, "name": "A"},
            {"horseNumber": 2, "name": "B"},
        ]
        self.assertEqual(rank_factor_model(self.race["horses"], self.race), [])

    def test_missing_single_factor_is_neutral_not_fake_completeness(self):
        self.race["horses"][0]["integratedEvaluation"]["v218Audit"].pop("sectional")
        row = next(z for z in rank_factor_model(self.race["horses"], self.race)
                   if z["horse"]["horseNumber"] == 1)
        self.assertEqual(row["primaryPillarCoverage"], 2)
        self.assertEqual(row["pillarScores"]["sectional"], None)
        self.assertAlmostEqual(row["score"], .45*.90+.35*.70+.20*.5)


if __name__ == "__main__":
    unittest.main()
