"""Stage64 existing pre-off engine boundary: no new strategy or hindsight."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import unittest

from arvexq.forecast.engine import build_prediction

JST = timezone(timedelta(hours=9))
BEFORE = datetime(2026, 10, 20, 10, 0, tzinfo=JST)
AFTER = datetime(2026, 10, 24, 10, 0, tzinfo=JST)


def race(owner):
    return {
        "id": owner + "-2026-10-23-" + ("京都" if owner == "jra" else "高知") + "-01",
        "date": "2026-10-23", "circuit": "中央" if owner == "jra" else "地方",
        "track": "京都" if owner == "jra" else "高知",
        "surface": "芝" if owner == "jra" else "ダート",
        "analysisMode": "平地", "startTime": "12:00", "fieldSize": 4,
        "horses": [
            {"horseNumber": no, "recentRaces": [{
                "date": "2026-10-15", "finish": no, "fieldSize": 4,
                "passing": [no], "track": "京都" if owner == "jra" else "高知",
            }]} for no in range(1, 5)
        ],
    }


class Stage64ProductionBoundary(unittest.TestCase):
    def test_jra_and_nar_six_stages_are_executed_without_data_mutation(self):
        for owner, scenario_count in (("jra", 1), ("nar", 4)):
            with self.subTest(circuit=owner):
                facts = race(owner)
                before = deepcopy(facts)
                result = build_prediction(facts, now=BEFORE)
                self.assertIsNotNone(result)
                self.assertEqual(facts, before)
                self.assertEqual(set(result["stages"]),
                                 {"ability", "runningStyle", "pace", "probability", "marks", "tickets"})
                self.assertEqual(result["circuit"], owner)
                self.assertEqual(len(result["stages"]["pace"]["value"]), scenario_count)
                self.assertAlmostEqual(sum(result["stages"]["probability"]["value"]["win"].values()), 1.0)
                self.assertIsNotNone(result["stages"]["marks"]["value"]["winRole"])
                self.assertIsNotNone(result["stages"]["marks"]["value"]["axisRole"])
                self.assertTrue(result["stages"]["tickets"]["value"]["hypotheticalTrifectaTop10"])
                self.assertIsNone(result["stages"]["marks"]["value"]["productMarks"])
                self.assertIsNone(result["stages"]["tickets"]["value"]["recommendedBets"])

    def test_post_off_naive_time_and_target_results_are_blocked(self):
        facts = race("nar")
        self.assertIsNone(build_prediction(facts, now=AFTER))
        self.assertIsNone(build_prediction(facts, now=BEFORE.replace(tzinfo=None)))
        facts["result"] = {"status": "確定"}
        self.assertIsNone(build_prediction(facts, now=BEFORE))

    def test_real_d1_preoff_result_placeholder_does_not_cancel_forecast(self):
        for owner in ("nar", "jra"):
            with self.subTest(owner=owner):
                detail = race(owner)
                detail["result"] = {"status": "未確定", "finishers": [],
                                    "payouts": []}
                before = deepcopy(detail)
                forecast = build_prediction(detail, now=BEFORE)
                self.assertIsNotNone(forecast)
                self.assertIsNotNone(forecast["stages"]["tickets"]["value"])
                self.assertEqual(detail, before)

    def test_actual_result_or_payout_never_recomputed(self):
        for outcome in ({"status": "速報"},
                        {"status": "確定", "finishers": []},
                        {"finishers": [{"horseNumber": 2, "finish": 1}]},
                        {"payouts": [{"type": "3連単", "amount": 1000}]}):
            with self.subTest(outcome=outcome):
                detail = race("nar")
                detail["result"] = outcome
                self.assertIsNone(build_prediction(detail, now=BEFORE))
        for key in ("results", "payouts"):
            detail = race("nar")
            detail[key] = [{"horseNumber": 1, "finish": 1}]
            self.assertIsNone(build_prediction(detail, now=BEFORE))

    def test_wrong_id_or_unknown_circuit_fails_closed(self):
        facts = race("jra")
        facts["circuit"] = "地方"
        self.assertIsNone(build_prediction(facts, now=BEFORE))
        facts["circuit"] = "unregistered"
        self.assertIsNone(build_prediction(facts, now=BEFORE))

    def test_missing_history_is_not_imputed(self):
        facts = race("nar")
        facts["horses"][0]["recentRaces"] = []
        result = build_prediction(facts, now=BEFORE)
        self.assertIsNotNone(result)
        self.assertEqual(result["stages"]["probability"]["status"], "blocked")
        self.assertIsNone(result["stages"]["tickets"]["value"])


if __name__ == "__main__":
    unittest.main()
