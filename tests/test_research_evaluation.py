import unittest
from copy import deepcopy
from datetime import datetime
from arvexq.prediction.research_shadow import build_shadow
from arvexq.prediction.research_evaluation import evaluate_race,summarize
from arvexq.prediction.prerace_archive import JST,seal_detail


class ResearchEvaluationTests(unittest.TestCase):
    def setUp(self):
        now=datetime(2026,10,8,19,30,tzinfo=JST)
        d={"id":"nar-2026-10-08-大井-11","date":"2026-10-08",
           "startTime":"20:00","circuit":"地方","track":"大井","horses":[]}
        for no in (1,2,3,4):
            d["horses"].append({"horseNumber":no,"name":f"H{no}",
              "recentRaces":[{"date":"2026-09-29","finish":no,"fieldSize":10,
                              "cornerPositions":[no,no,no,no]}]})
        lock={"raceId":d["id"],"raceDate":d["date"],
              "capturedAtEpoch":int(now.timestamp()),
              "horses":[{"horseNumber":no,"mark":("◎" if no==1 else "○" if no==2
                         else "▲" if no==3 else "")} for no in (1,2,3,4)]}
        self.d=seal_detail(d,lock,now)
        self.d["result"]={"status":"確定","finishers":[
            {"finish":1,"horseNumber":1},{"finish":2,"horseNumber":2},
            {"finish":3,"horseNumber":3},{"finish":4,"horseNumber":4}]}

    def test_only_genuine_preoff_sealed_shadow_is_compared(self):
        evaluated=evaluate_race(self.d)
        self.assertIsNotNone(evaluated)
        self.assertEqual(evaluated["actual"],[1,2,3])
        self.assertEqual(evaluated["lockedHonmeiTop3"],True)
        self.assertLess(evaluated["shadowBrierWin"],1.)

    def test_post_result_recalculation_is_not_evidence(self):
        d=deepcopy(self.d)
        d["researchShadow"]=build_shadow(d)
        d["researchShadow"]["rows"][0]["uncalibrated"]["p1"]=.99
        self.assertIsNone(evaluate_race(d))

    def test_absent_preoff_snapshot_cannot_join(self):
        d=deepcopy(self.d)
        d.pop("preRacePrediction")
        self.assertIsNone(evaluate_race(d))

    def test_nonfinal_result_cannot_join(self):
        d=deepcopy(self.d)
        d["result"]["status"]="速報"
        self.assertIsNone(evaluate_race(d))

    def test_research_cannot_auto_promote_or_claim_roi(self):
        info=summarize([evaluate_race(self.d)],min_races=1)
        self.assertFalse(info["promotionEligible"])
        self.assertEqual(info["readiness"],"candidate-for-further-calibration-and-forward-validation")
        self.assertNotIn("roi",info)
        self.assertEqual(info["shadowTopThreeCoverageAverage"],3.)


if __name__=="__main__":
    unittest.main()
