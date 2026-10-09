"""Lossless historical transfer invariants; never hide missing starts."""
from __future__ import annotations
import copy
import unittest
from arvexq.ingest.career_transport import pack_detail, pack_horse, recover_horse
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.career_profile import profile_career

RACE={"date":"2026-10-10","track":"大井","distance":1200,"surface":"ダート","condition":"良"}
def run(month,day,finish=2):
    return {"date":f"2026-{month:02d}-{day:02d}","track":"大井","raceNumber":3,
            "distance":1200,"surface":"ダート","condition":"良","fieldSize":12,
            "finish":finish,"cornerPositions":[1,3,3,3],
            "title":"C1 race","timeSeconds":72.1,"jockey":"test"}

class CareerTransportTest(unittest.TestCase):
    def setUp(self):
        dates=[(2,1),(2,7),(2,15),(2,24),(3,1),(3,7),(3,15),(3,24),
               (4,1),(4,7),(4,15),(4,24),(5,1),(5,7),(5,15),
               (6,1),(6,7),(6,15),(7,1),(7,7),(7,15),
               (8,1),(8,7),(8,15),(9,1),(9,7),(9,15),(9,24)]
        self.runs=[run(m,d,1 if i%4==0 else 6) for i,(m,d) in enumerate(dates)]
        self.horse={"horseNumber":1,"name":"test","recentRaces":self.runs[-5:],
            "allPastRuns":self.runs,
            "_careerHistoryAudit":{"complete":False}}
    def test_transport_is_lossless_with_visible_five(self):
        raw=copy.deepcopy(self.horse)
        packed=pack_horse(raw,RACE["date"])
        self.assertEqual(len(packed["allPastRuns"]),28)
        self.assertEqual(packed["careerTransport"]["compactOlderRuns"],23)
        self.assertTrue(all("timeSeconds" in r for r in packed["allPastRuns"]))
        self.assertEqual(len(packed["recentRaces"]),5)
        self.assertEqual(packed["careerArchive"]["olderRunCount"],23)
        self.assertEqual(packed["careerTransport"]["observedRuns"],28)
        restored=recover_horse(packed,RACE["date"])
        self.assertEqual(restored["allPastRuns"],list(reversed(self.runs)))
        # Incoming runs are sorted newest first, but the source input stays unchanged.
        self.assertEqual(raw,self.horse)
        self.assertEqual(profile_career(restored,RACE)["datedRuns"],28)
        self.assertEqual(len(observed_runs(packed,RACE,limit=None)),28)
        self.assertEqual(len(observed_runs(packed,RACE)),5)
        self.assertEqual(pack_horse(packed,RACE["date"]),packed)
    def test_corruption_must_fail_closed(self):
        packed=pack_horse(self.horse,RACE["date"])
        packed["careerArchive"]["sha256"]="0"*64
        with self.assertRaises(ValueError):
            recover_horse(packed,RACE["date"])
        with self.assertRaises(ValueError):
            recover_horse(packed,"2026-10-09")
    def test_protected_d1_upsert_merges_two_archives_without_rewriting_morning(self):
        from scripts.arvexq_protect_sync import protect_detail
        old_horse=pack_horse(self.horse,RACE["date"])
        newer=copy.deepcopy(self.horse)
        newer["allPastRuns"]=self.runs[12:]+[run(9,29,1)]
        new_horse=pack_horse(newer,RACE["date"])
        baseline={"version":"arvexq-morning-marks-v1","raceId":"race","fixedAt":"2026-10-10T07:00:00+09:00"}
        old={"id":"race","date":RACE["date"],"horses":[old_horse],
             "morningMarkSnapshot":baseline}
        incoming={"id":"race","date":RACE["date"],"horses":[new_horse],
                  "morningMarkSnapshot":{**baseline,"fixedAt":"modified"}}
        result=protect_detail(old,incoming)
        self.assertEqual(result["morningMarkSnapshot"],baseline)
        full=recover_horse(result["horses"][0],RACE["date"])
        self.assertEqual(len(full["allPastRuns"]),29)
        self.assertEqual(full["allPastRuns"][0]["date"],"2026-09-29")
        self.assertEqual(full["allPastRuns"][-1]["date"],"2026-02-01")
        self.assertEqual(result["horses"][0]["careerTransport"]["observedRuns"],29)

    def test_date_cutoff_and_diagnosis_survive_pack(self):
        horse=copy.deepcopy(self.horse)
        horse["allPastRuns"].append(run(10,11,1))
        horse["integratedEvaluation"]={"mark":"◎","careerProfile":profile_career(horse,RACE)}
        detail=pack_detail({"date":"2026-10-10","id":"race","horses":[horse],
                            "morningMarkSnapshot":{"sealed":True}})
        self.assertEqual(detail["morningMarkSnapshot"],{"sealed":True})
        self.assertEqual(detail["horses"][0]["integratedEvaluation"]["mark"],"◎")
        self.assertEqual(detail["horses"][0]["integratedEvaluation"]["careerProfile"]["datedRuns"],28)
        self.assertEqual(recover_horse(detail["horses"][0],RACE["date"])["allPastRuns"][0]["date"],"2026-09-24")

if __name__=="__main__":
    unittest.main()
