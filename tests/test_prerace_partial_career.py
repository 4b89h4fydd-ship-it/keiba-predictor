"""Do not seal from the retired partial-career/three-factor fallback."""
import copy
import unittest
from datetime import datetime,timedelta
from arvexq.prediction.prerace_archive import JST
from arvexq.prediction.final_marks import apply_core_marks
from scripts.arvexq_freeze_predictions import prepare_seal

NOW=datetime(2026,10,13,12,0,tzinfo=JST)

def race():
    horses=[]
    for no in range(1,8):
        runs=[{"date":f"2026-09-{d:02d}","track":"東京","surface":"芝",
               "distance":1800,"fieldSize":12,"finish":min(no,12),
               "cornerPositions":[no,no], "marginSeconds":(no-1)*.3,
               "marginEvidenceSource":"JRA official",
               "marginEvidence":{"winnerTimeSeconds":110.0,
                                 "horseTimeSeconds":110.0+(no-1)*.3}}
              for d in (3,10,17,24,27)]
        horses.append({"horseNumber":no,"frameNumber":no,"name":f"Horse-{no}",
                       "recentRaces":runs,"allPastRuns":copy.deepcopy(runs)})
    return {"id":"jra-2026-10-13-東京-11","date":"2026-10-13","circuit":"中央",
            "track":"東京","raceNumber":11,"startTime":"12:30",
            "fieldSize":7,"surface":"芝","distance":1800,"horses":horses}

def build(d):
    return {"raceId":d["id"],"raceDate":d["date"],"capturedAtEpoch":int(NOW.timestamp()),
            "markCount":sum(bool(h.get("integratedEvaluation",{}).get("mark")) for h in d["horses"]),
            "horses":[{"horseNumber":h["horseNumber"],
                        "mark":h.get("integratedEvaluation",{}).get("mark","")}
                       for h in d["horses"]]}

class OfficialEvidenceSealTests(unittest.TestCase):
    def test_all_observed_runners_can_seal_without_old_partial_career_path(self):
        d=race()
        before=copy.deepcopy(d)
        marks=apply_core_marks(copy.deepcopy(d))
        self.assertEqual(marks["predictionStatus"],"ready")
        self.assertEqual(marks["predictionModelVersion"],"arvexq-jra-observed-consensus-v1")
        sealed=prepare_seal(d,now=NOW,assign=apply_core_marks,build=build)
        self.assertEqual(sealed["status"],"sealed",sealed)
        self.assertEqual(d,before)
        self.assertEqual(sum(h["mark"]=="◎" for h in sealed["detail"]["preRacePrediction"]["horses"]),1)

    def test_one_unverified_horse_blocks_original_before_off(self):
        d=race()
        for q in d["horses"][-1]["recentRaces"]+d["horses"][-1]["allPastRuns"]:
            q.pop("marginEvidence",None)
        sealed=prepare_seal(d,now=NOW,assign=apply_core_marks,build=build)
        self.assertEqual(sealed["status"],"incomplete-prediction")
        self.assertEqual(sealed["observedCoverage"]["fullyObserved"],6)
        self.assertNotIn("preRacePrediction",d)

    def test_no_margin_never_calls_old_ranker_to_invent_seal(self):
        d=race()
        for h in d["horses"]:
            for q in h["recentRaces"]+h["allPastRuns"]:
                q.pop("marginSeconds",None)
        result=prepare_seal(d,now=NOW,assign=apply_core_marks,
                            build=lambda _:self.fail("old-model fallback invoked"))
        self.assertEqual(result["status"],"incomplete-prediction")

    def test_after_off_never_creates_original(self):
        d=race()
        result=prepare_seal(d,now=NOW+timedelta(minutes=31),assign=apply_core_marks,build=build)
        self.assertEqual(result["status"],"started-no-new-lock")

if __name__=="__main__":unittest.main()
