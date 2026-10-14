"""A Mineta comparison is eligible only with observed prior-run margins for all horses."""
import unittest
from scripts.arvexq_mineta_evidence_complete_pilot import candidate_run, official_observation

class MinetaCompleteObservationTest(unittest.TestCase):
    def test_official_time_gap_and_raw_sectional(self):
        key=("2026-10-01","金沢",4)
        data={"finishers":[
            {"name":"勝馬","finish":1,"timeSeconds":75.0},
            {"name":"対象馬","finish":2,"timeSeconds":75.4,"last3FSeconds":38.4}]}
        observed,reason=official_observation(key,"対象馬",
            {"date":"2026-10-01","fieldSize":8,"finish":2},data)
        self.assertEqual(reason,"observed")
        self.assertEqual(observed["timeBehindWinner"],.4)
        self.assertEqual(observed["last3fSeconds"],38.4)
        self.assertEqual(observed["fieldSize"],8)
        self.assertNotIn("opponentLevel",observed)
        self.assertNotIn("last3fRank",observed)

    def test_reject_absent_winner_and_name_collisions(self):
        key=("2026-10-01","金沢",4)
        data={"finishers":[{"name":"同名","finish":2,"timeSeconds":75.4},
                             {"name":"同名","finish":3,"timeSeconds":75.8}]}
        self.assertEqual(official_observation(key,"同名",{},data)[0],None)
        data["finishers"].append({"name":"勝馬","finish":1,"timeSeconds":75.0})
        self.assertEqual(official_observation(key,"同名",{},data)[0],None)

    def test_only_prior_races_and_trusted_number(self):
        self.assertIsNone(candidate_run({"date":"2026-10-13","track":"金沢","raceNumber":4},"2026-10-13"))
        self.assertIsNone(candidate_run({"date":"2026-10-12","track":"金沢","raceNumber":14},"2026-10-13"))
        self.assertIsNone(candidate_run({"date":"2026-10-12","track":"京都","raceNumber":4},"2026-10-13"))
        self.assertEqual(candidate_run({"date":"2026-10-12","track":"金沢","raceNumber":4},"2026-10-13"),
                         ("2026-10-12","金沢",4))

if __name__=="__main__":
    unittest.main()
