from __future__ import annotations
import unittest
from arvexq.databanks.legacy_bridge import _nar_official_past_result_adapter

class NarOfficialHistoryTests(unittest.TestCase):
    def test_only_prior_observed_horse_result_is_used(self):
        queried = []
        def official(detail):
            queried.append(detail)
            return {"finishers": [
                {"finish": 1, "name": "勝馬", "timeSeconds": 75.0},
                {"finish": 2, "name": "対象馬", "timeSeconds": 75.4,
                 "last3FSeconds": 37.8, "marginText": "２"},
            ]}
        fetch = _nar_official_past_result_adapter({"_nar_official_result_fast":official})
        out = fetch({"name": "対象馬", "recentRaces": [{
            "date":"2026-09-01","track":"大井","raceNumber":4,"finish":2
        }]}, {"date":"2026-09-15"}, 5)
        self.assertEqual(len(queried), 1)
        observed = out["recentRaces"][0]
        self.assertEqual(observed["last3fSeconds"], 37.8)
        self.assertEqual(observed["marginText"], "２")
        self.assertAlmostEqual(observed["timeBehindWinner"], 0.4)

    def test_future_and_ambiguous_horses_rejected(self):
        count=[]
        def official(detail):
            count.append(detail)
            return {"finishers":[{"name":"同名","finish":1,"last3FSeconds":36.0},
                                 {"name":"同名","finish":2,"last3FSeconds":36.4}]}
        fetch=_nar_official_past_result_adapter({"_nar_official_result_fast":official})
        h={"name":"同名","recentRaces":[{"date":"2026-09-16","track":"大井","raceNumber":2}]}
        self.assertEqual(fetch(h,{"date":"2026-09-15"}),{})
        self.assertEqual(count,[])
        h["recentRaces"][0]["date"]="2026-09-01"
        self.assertEqual(fetch(h,{"date":"2026-09-15"}),{})

    def test_restore_only_official_unique_zero_finish(self):
        fetch = _nar_official_past_result_adapter({"_nar_official_result_fast":
            lambda r: {"finishers":[{"name":"対象馬","finish":1},{"name":"他馬","finish":2}]}})
        horse={"name":"対象馬","recentRaces":[{"date":"2026-10-04","track":"高知","raceNumber":1,"fieldSize":5,"finish":0}]}
        observed=fetch(horse,{"date":"2026-10-17"})["recentRaces"][0]
        self.assertEqual(observed["finish"],1)
        self.assertTrue(observed["researchOfficialPriorFinishVerified"])

    def test_ambiguous_official_result_does_not_restore(self):
        fetch=_nar_official_past_result_adapter({"_nar_official_result_fast":
            lambda r: {"finishers":[{"name":"対象馬","finish":1},{"name":"対象馬","finish":2}]}})
        horse={"name":"対象馬","recentRaces":[{"date":"2026-10-04","track":"高知","raceNumber":1,"fieldSize":5,"finish":0}]}
        self.assertEqual(fetch(horse,{"date":"2026-10-17"}),{})

    def test_existing_history_merges_require_verification_for_zero(self):
        from arvexq.ingest.full_career import merge_career
        from arvexq.ingest.fallback_enrichment import _merge_runs
        base={"date":"2026-10-04","track":"高知","raceNumber":1,"fieldSize":5,"finish":0}
        verified={**base,"finish":1,"researchOfficialPriorFinishVerified":True}
        unverified={**base,"finish":1}
        self.assertEqual(merge_career([base],[verified],"2026-10-17")[0]["finish"],1)
        self.assertEqual(merge_career([base],[unverified],"2026-10-17")[0]["finish"],0)
        self.assertEqual(_merge_runs([base],[verified],cutoff="2026-10-17")[0]["finish"],1)
        self.assertEqual(_merge_runs([base],[unverified],cutoff="2026-10-17")[0]["finish"],0)

if __name__=="__main__":
    unittest.main()
