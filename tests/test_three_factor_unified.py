"""Tests the three measured pre-off factors, marks and no legacy weights."""
import copy
import unittest
from unittest.mock import patch

from arvexq.prediction.factor_model import (
    MODEL_VERSION, PRIMARY_PILLARS, SCORE_WEIGHTS,
    collect_horse_raw_metrics, rank_factor_model,
)
from arvexq.prediction.final_marks import apply_core_marks


class UnifiedThreeFactorTests(unittest.TestCase):
    def setUp(self):
        self.race = {"date": "2026-10-13", "circuit": "地方", "track": "園田",
                     "distance": 1400, "surface": "ダート", "horses": []}
        finishes = {
            1: [1, 2, 1, 2, 1],
            2: [1, 3, 2, 3, 4],
            3: [2, 3, 4, 5, 4],
            4: [5, 6, 4, 7, 6],
            5: [9, 8, 7, 10, 9],
        }
        for num, rank in finishes.items():
            runs = [
                {"date": f"2026-10-{day:02d}", "finish": rank[i],
                 "fieldSize": 12, "last3fRank": rank[i],
                 "track": "園田", "distance": 1400}
                for i, day in enumerate([11, 9, 7, 5, 3])
            ]
            self.race["horses"].append({
                "horseNumber": num, "name": f"Horse{num}",
                "recentRaces": copy.deepcopy(runs),
                "allPastRuns": copy.deepcopy(runs),
                "integratedEvaluation": {"v218Audit": {
                    "trueRun": 0.0, "pure": 0.0, "sectional": 0.0}},
            })

    def test_weights_use_observed_runs_and_ignore_old_composites(self):
        ranking = rank_factor_model(self.race["horses"], self.race)
        self.assertEqual(PRIMARY_PILLARS, ("trueRun", "pure", "sectional"))
        self.assertEqual(SCORE_WEIGHTS, {"trueRun": .45, "pure": .35, "sectional": .20})
        self.assertIn("45-35-20", MODEL_VERSION)
        self.assertEqual(ranking[0]["horse"]["horseNumber"], 1)
        self.assertEqual(ranking[0]["primaryPillarCoverage"], 3)
        q = ranking[0]["pillarScores"]
        self.assertGreater(q["trueRun"], .8)
        self.assertGreater(q["pure"], .8)
        self.assertAlmostEqual(ranking[0]["score"],
                               .45*q["trueRun"]+.35*q["pure"]+.20*q["sectional"])
        self.assertNotIn("ability", q)
        self.assertNotIn("pace", q)

    def test_marks_use_exactly_this_order(self):
        def ready(detail):
            detail["careerReadiness"] = {"ready": True, "activeHorses": 5,
                                          "completeHorses": 5}
            return detail
        with patch("arvexq.prediction.final_marks.attach_career_readiness",
                   side_effect=ready):
            detail = apply_core_marks(copy.deepcopy(self.race))
        ordered = sorted(detail["horses"], key=lambda h: h["integratedEvaluation"]["rank"])
        # Fifth rank does not automatically earn ☆; this fixture has weak
        # independent factors for Horse5.
        self.assertEqual([h["integratedEvaluation"]["mark"] for h in ordered],
                         ["◎", "○", "▲", "△", ""])
        self.assertEqual(detail["honmeiDecision"]["horseNumber"], ordered[0]["horseNumber"])
        self.assertEqual(sum(h["integratedEvaluation"]["mark"] == "◎" for h in ordered), 1)
        self.assertNotIn("multiHeadSummary", detail)

    def test_all_missing_does_not_fabricate_rank(self):
        self.race["horses"] = [
            {"horseNumber": 1, "name": "A"},
            {"horseNumber": 2, "name": "B"},
        ]
        self.assertEqual(rank_factor_model(self.race["horses"], self.race), [])

    def test_missing_sectional_is_neutral_with_explicit_coverage(self):
        h = self.race["horses"][0]
        for r in h["recentRaces"] + h["allPastRuns"]:
            r.pop("last3fRank", None)
        row = next(z for z in rank_factor_model(self.race["horses"], self.race)
                   if z["horse"]["horseNumber"] == 1)
        self.assertEqual(row["primaryPillarCoverage"], 2)
        self.assertIsNone(row["pillarScores"]["sectional"])
        v = row["pillarScores"]
        self.assertAlmostEqual(row["score"], .45*v["trueRun"]+.35*v["pure"]+.20*.5)

    def test_future_results_and_old_model_do_not_affect_score(self):
        h=self.race["horses"][4]
        before=collect_horse_raw_metrics(h,self.race)
        h["recentRaces"].append({"date":"2026-10-14","finish":1,"fieldSize":12,
                                  "last3fRank":1})
        h["integratedEvaluation"]["v218Audit"]={"trueRun":1,"pure":1,"sectional":1}
        after=collect_horse_raw_metrics(h,self.race)
        self.assertEqual(before,after)


if __name__=="__main__":
    unittest.main()
