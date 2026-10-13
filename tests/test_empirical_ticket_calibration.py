import unittest
from scripts.arvexq_empirical_ticket_calibration import (
    MODEL, sealed_result, summarize, ticket_hit, wilson_lower, selected_main_ticket,
)
class EmpiricalHitCalibrationTests(unittest.TestCase):
    def ticket(self, at, kind="ワイド", engine=MODEL):
        return {
            "id": "nar-2026-10-12-園田-01", "date": "2026-10-12",
            "startTime": "14:10", "raceStatus": "確定",
            "preRaceBet": {"fixedAt": at, "engineVersion": engine,
                           "decision": "購入候補",
                           "items": [{"level": "本線", "kind": kind,
                                      "combos": [[1, 3]]}]},
            "result": {"status": "確定", "finishers": [
                {"finish": 1, "horseNumber": 1},
                {"finish": 2, "horseNumber": 2},
                {"finish": 3, "horseNumber": 3},
            ]},
        }
    def test_preoff_wide_hit(self):
        item = sealed_result(self.ticket("2026-10-12T13:30:00+09:00"), "2026-10-13")
        self.assertIsNotNone(item)
        self.assertTrue(item["hit"])
        self.assertEqual(item["kind"], "ワイド")
    def test_no_leakage_or_old_model(self):
        self.assertIsNone(sealed_result(self.ticket("2026-10-12T14:11:00+09:00"), "2026-10-13"))
        self.assertIsNone(sealed_result(self.ticket("2026-10-12T13:30:00+09:00",engine="old-score"), "2026-10-13"))
        self.assertIsNone(sealed_result(self.ticket("2026-10-12T13:30:00+09:00"), "2026-10-12"))
        self.assertFalse(ticket_hit("馬連", [1, 3], (1,2,3)))
        self.assertTrue(ticket_hit("ワイド", [1, 3], (1,2,3)))
    def test_fail_closed_without_sample(self):
        record = {"x": {"id":"x","date":"2026-10-12","model":MODEL,"kind":"ワイド","points":1,"hit":True}}
        result=summarize(record,"2026-10-13")
        self.assertFalse(result["buckets"]["ワイド|1"]["qualified"])
        self.assertEqual(result["status"],"insufficient-evidence")
        self.assertLess(wilson_lower(1,1),.65)
    def test_calibrated_group_needs_real_hit_rate(self):
        examples={str(i):{"id":str(i),"date":"2026-10-12","model":MODEL,"kind":"ワイド","points":1,"hit":i<28} for i in range(32)}
        res=summarize(examples,"2026-10-13")
        self.assertTrue(res["buckets"]["ワイド|1"]["qualified"])
        examples.update({str(i):{"id":str(i),"date":"2026-10-12","model":MODEL,"kind":"ワイド","points":1,"hit":False} for i in range(9)})
        self.assertFalse(summarize(examples,"2026-10-13")["buckets"]["ワイド|1"]["qualified"])
if __name__=="__main__": unittest.main()
