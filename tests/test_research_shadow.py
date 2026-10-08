import copy
import math
import unittest
from datetime import datetime
from arvexq.prediction.research_shadow import build_shadow, horse_evidence, ordered_probabilities
from arvexq.prediction.mass_feature_factory import build_horse_features
from arvexq.prediction.mass_model_training import HEAD_SPECS


class ResearchShadowTests(unittest.TestCase):
    def setUp(self):
        self.race={"id":"jra-test-2026-10-08","date":"2026-10-08","track":"東京",
                   "surface":"芝","distance":1600,"condition":"良"}
        self.h={"horseNumber":1,"recentRaces":[
            {"date":"2026-09-21","track":"東京","distance":1600,"surface":"芝",
             "condition":"良","fieldSize":12,"finish":3,"cornerPositions":[2,2,4,4],
             "last3FRank":2,"timeSeconds":94.2,"speedIndex":87},
            {"date":"2026-09-12","track":"東京","distance":1600,"surface":"芝",
             "condition":"良","fieldSize":12,"finish":2,"cornerPositions":[4,4,3,3],
             "last3FRank":3,"timeSeconds":95.3},
            {"date":"2026-10-10","track":"東京","distance":1600,"surface":"芝",
             "condition":"良","fieldSize":12,"finish":1,"cornerPositions":[1,1,1,1],
             "timeSeconds":85., "speedIndex":110}]}

    def test_only_previous_runs_used_in_stage_evidence(self):
        ev=horse_evidence(self.h,self.race)
        self.assertEqual(ev["historyCount"],2)
        self.assertEqual(ev["matchedClockCount"],2)
        self.assertTrue(0<ev["frontStartRate"]<1)
        self.assertEqual(ev["sampledStages"]["start"],2)

    def test_future_result_and_odds_cannot_affect_shadow(self):
        d={**self.race,"horses":[
           copy.deepcopy(self.h), {"horseNumber":2,"recentRaces":self.h["recentRaces"][:2]},
           {"horseNumber":3,"recentRaces":self.h["recentRaces"][:2]}]}
        a=build_shadow(d)
        d["result"]={"finishers":[{"horseNumber":1,"finish":1}]}
        d["horses"][0]["winOdds"]=1.1
        d["horses"][0]["recentRaces"][2]["finish"]=9
        b=build_shadow(d)
        self.assertEqual(a,b)

    def test_marginals_and_exact_trifecta_are_normalized(self):
        probs,triples=ordered_probabilities([2.,1.,3.,4.])
        self.assertEqual(len(probs),4)
        for k in ("p1","p2","p3"):
            self.assertAlmostEqual(sum(x[k] for x in probs),1.,places=9)
        self.assertAlmostEqual(sum(x["top3"] for x in probs),3.,places=9)
        self.assertEqual(len(triples),24)
        self.assertAlmostEqual(sum(x["score"] for x in triples),1.,places=9)

    def test_insufficient_historical_coverage_cannot_fake_ordered_odds(self):
        r={**self.race,"horses":[{"horseNumber":1}, {"horseNumber":2}, {"horseNumber":3}]}
        shadow=build_shadow(r)
        self.assertFalse(shadow["evidenceSufficientForShadow"])
        self.assertTrue(all(row["uncalibrated"] is None for row in shadow["rows"]))
        self.assertEqual(shadow["orderedTrifectaShadow"],[])

    def test_missing_history_is_not_replaced_with_fake_quality(self):
        result=horse_evidence({"horseNumber":1},self.race)
        self.assertIsNone(result["closingPercentile"])
        self.assertEqual(result["historyCount"],0)

    def test_mass_features_no_future_leak_and_no_speed_mixing(self):
        features=build_horse_features(self.h,self.race)
        self.assertEqual(features["history::all::w5::run_count"],2.)
        self.assertEqual(features["history::all::w5::speed::count"],1.)
        self.assertEqual(features["history::all::w5::speed::last"],87.)
        self.assertNotIn("history::all::w5::clock_speed::count",features)
        self.assertEqual(features["history::matched_clock_context::w5::clock_speed::count"],2.)
        self.assertLess(features["history::matched_clock_context::w5::clock_speed::mean"],20.)

    def test_podium_head_is_available_in_lightweight_runtime(self):
        from inspect import getsource
        from arvexq.prediction.mass_model_runtime import MassModelRuntime
        self.assertIn('"podium"',getsource(MassModelRuntime.predict_heads))
        self.assertIn('"win"',getsource(MassModelRuntime.predict_heads))

    def test_podium_model_head_is_independent_of_win(self):
        self.assertEqual(HEAD_SPECS["podium"].label,"labelTop3")
        self.assertEqual(HEAD_SPECS["win"].label,"labelWin")
        self.assertFalse(HEAD_SPECS["podium"].include_feature("market::popularity"))


if __name__=="__main__":
    unittest.main()
