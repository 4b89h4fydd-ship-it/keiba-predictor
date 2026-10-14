import unittest
from unittest.mock import patch
from scripts.arvexq_empirical_ticket_calibration import (
    MODELS, sealed_result, summarize, ticket_hit, wilson_lower, selected_main_ticket, fetch_previous_day,
)
MODEL = MODELS['地方']

class EmpiricalHitCalibrationTests(unittest.TestCase):
    def ticket(self, at, kind="ワイド", engine=MODEL):
        return {
            "id": "nar-2026-10-12-園田-01", "date": "2026-10-12", "circuit":"地方",
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
    def test_circuit_qualifications_are_not_interchangeable(self):
        records = {}
        for i in range(32):
            records["nar-"+str(i)] = {"date":"2026-10-12","circuit":"地方",
                "model": MODELS["地方"],"kind":"ワイド","points":1,"hit":i<28}
            records["jra-"+str(i)] = {"date":"2026-10-12","circuit":"中央",
                "model": MODELS["中央"],"kind":"ワイド","points":1,"hit":False}
        result = summarize(records, "2026-10-13")
        self.assertTrue(result["byCircuit"]["地方"]["buckets"]["ワイド|1"]["qualified"])
        self.assertFalse(result["byCircuit"]["中央"]["buckets"]["ワイド|1"]["qualified"])
        self.assertEqual(result["byCircuit"]["地方"]["totalVerifiedRaces"], 32)
        self.assertEqual(result["byCircuit"]["中央"]["totalVerifiedRaces"], 32)
        legacy = {"old": {"date":"2026-10-12","circuit":"地方",
            "model":"arvexq-form-condition-no-sectional-proposal-v1",
            "kind":"ワイド","points":1,"hit":True}}
        self.assertEqual(summarize(legacy,"2026-10-13")["totalVerifiedRaces"], 0)

    def test_failed_day_fetch_is_not_zero_sample(self):
        with patch("scripts.arvexq_empirical_ticket_calibration.get_json", side_effect=OSError("offline")):
            with self.assertRaisesRegex(RuntimeError, "HIT_RATE_DAY_UNAVAILABLE"):
                fetch_previous_day("https://example.invalid", "2026-10-13")

    def test_failed_race_fetch_is_not_zero_sample(self):
        def fake_fetch(url):
            if "/api/day?" in url:
                return {"races": [{"id": "race-1"}]}
            raise OSError("race offline")
        with patch("scripts.arvexq_empirical_ticket_calibration.get_json", side_effect=fake_fetch):
            with self.assertRaisesRegex(RuntimeError, "HIT_RATE_RACE_UNAVAILABLE"):
                fetch_previous_day("https://example.invalid", "2026-10-13")

    def test_bad_day_shape_rejected(self):
        with patch("scripts.arvexq_empirical_ticket_calibration.get_json", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "HIT_RATE_DAY_INVALID"):
                fetch_previous_day("https://example.invalid", "2026-10-13")

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
        record = {"x": {"id":"x","date":"2026-10-12","circuit":"地方","model":MODEL,"kind":"ワイド","points":1,"hit":True}}
        result=summarize(record,"2026-10-13")
        self.assertFalse(result["byCircuit"]["地方"]["buckets"]["ワイド|1"]["qualified"])
        self.assertEqual(result["status"],"insufficient-evidence")
        self.assertLess(wilson_lower(1,1),.65)
    def test_calibrated_group_needs_real_hit_rate(self):
        examples={str(i):{"id":str(i),"date":"2026-10-12","model":MODEL,"kind":"ワイド","points":1,"hit":i<28} for i in range(32)}
        res=summarize(examples,"2026-10-13")
        self.assertTrue(res["buckets"]["ワイド|1"]["qualified"])
        examples.update({str(i):{"id":str(i),"date":"2026-10-12","model":MODEL,"kind":"ワイド","points":1,"hit":False} for i in range(9)})
        self.assertFalse(summarize(examples,"2026-10-13")["buckets"]["ワイド|1"]["qualified"])
if __name__=="__main__": unittest.main()
