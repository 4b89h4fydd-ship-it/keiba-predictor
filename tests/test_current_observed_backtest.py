"""Historical replay must not use race result as a prediction feature."""
import copy
import unittest
from unittest.mock import patch
from scripts.arvexq_current_observed_backtest import evaluate

class HistoricalCurrentModelTests(unittest.TestCase):
    def test_replay_strips_current_finish_and_odds_and_counts_hits(self):
        record={"id":"nar-2099-01-01-test","circuit":"地方","date":"2099-01-01",
                "result":{"finishers":[{"horseNumber":1,"finish":1},{"horseNumber":2,"finish":2},
                                       {"horseNumber":3,"finish":3}]},
                "horses":[{"horseNumber":i,"name":str(i),"winOdds":1.5,"popularity":i,
                           "integratedEvaluation":{"score":100},
                           "recentRaces":[{"date":"2098-12-01","finish":2,"fieldSize":8}]}
                          for i in range(1,4)]}
        original=copy.deepcopy(record)
        def scorer(pre):
            self.assertNotIn("result",pre)
            for h in pre["horses"]:
                self.assertNotIn("winOdds",h)
                self.assertNotIn("popularity",h)
                self.assertNotIn("integratedEvaluation",h)
            pre["predictionStatus"]="ready"
            pre["factorRanking"]=[{"horseNumber":1},{"horseNumber":2},{"horseNumber":3}]
        with patch("scripts.arvexq_current_observed_backtest.apply_observed_marks",side_effect=scorer):
            report=evaluate([record])
        self.assertEqual(report["counts"]["top1"],1)
        self.assertEqual(report["counts"]["top3"],1)
        self.assertEqual(report["counts"]["scored"],1)
        self.assertEqual(record,original)

    def test_incomplete_inputs_not_reported_as_accuracy(self):
        d={"id":"jra-empty","circuit":"中央","date":"2099-01-01",
           "horses":[{"horseNumber":1}],"result":{"finishers":[{"horseNumber":1,"finish":1}]}}
        def scorer(pre):
            pre["predictionStatus"]="insufficient-observed-inputs"
            pre["factorRanking"]=[]
            pre["observedModelCoverage"]={"horses":1,"fullyObserved":0}
        with patch("scripts.arvexq_current_observed_backtest.apply_observed_marks",side_effect=scorer):
            report=evaluate([d])
        self.assertEqual(report["counts"].get("scored",0),0)
        self.assertEqual(report["counts"]["incomplete_current_6040"],1)
