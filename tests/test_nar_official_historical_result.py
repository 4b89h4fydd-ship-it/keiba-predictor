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

if __name__=="__main__":
    unittest.main()
