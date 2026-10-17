"""JRA/NAR transfers must not mix uncomparable career rate denominators."""
import unittest
from arvexq.ingest.transfer_history import _history_rates, _run_circuit


class TransferRatesTests(unittest.TestCase):
    def test_track_classifier_and_missing_track(self):
        self.assertEqual(_run_circuit({"track": "京都"}), "JRA")
        self.assertEqual(_run_circuit({"track": "大井"}), "NAR")
        self.assertIsNone(_run_circuit({"track": "不明"}))

    def test_jra_to_nar_is_separated(self):
        horse={"horseNumber": 1, "recentRaces": [
            {"date":"2026-09-25","track":"大井","finish":2,"fieldSize":12},
            {"date":"2026-09-15","track":"東京","finish":1,"fieldSize":12},
            {"date":"2026-09-01","track":"京都","finish":1,"fieldSize":12},
        ]}
        result=_history_rates(horse,{"date":"2026-10-01","circuit":"地方"})
        self.assertEqual(result["starts"],1)
        self.assertEqual(result["otherCircuitStarts"],2)
        self.assertEqual(result["winRate"],0)
        self.assertEqual(result["top2Rate"],1)
        self.assertTrue(result["transferEvidence"])

    def test_future_runs_never_count(self):
        horse={"horseNumber":1,"recentRaces":[
            {"date":"2026-10-15","track":"園田","finish":1,"fieldSize":12},
            {"date":"2026-09-15","track":"園田","finish":3,"fieldSize":12}]}
        result=_history_rates(horse,{"date":"2026-10-01","circuit":"地方"})
        self.assertEqual(result["starts"],1)
        self.assertEqual(result["winRate"],0)
        self.assertEqual(result["top3Rate"],1)

if __name__ == "__main__":
    unittest.main()
