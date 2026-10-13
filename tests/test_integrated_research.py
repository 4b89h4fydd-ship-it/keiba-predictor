import copy
import unittest
from scripts.arvexq_integrated_research import eligible, probability_vector, summarize


def detail():
    return {"id": "r", "date": "2026-10-10", "startTime": "12:00", "circuit": "地方",
            "preRacePrediction": {"raceId": "r", "raceDate": "2026-10-10", "frozen": True,
                "capturedAtEpoch": 1791600000, "horses": [
                    {"horseNumber": i, "mark": "", "decisionProbability": p,
                     "p1Probability": p, "p2Probability": 1/3, "p3Probability": 1/3}
                    for i, p in ((1, .5), (2, .3), (3, .2))]},
            "result": {"status": "確定", "finishers": [
                {"finish": i, "horseNumber": i} for i in (1, 2, 3)]}}


class AuditTests(unittest.TestCase):
    def test_forecast_is_frozen_and_input_remains_immutable(self):
        d = detail()
        original = copy.deepcopy(d)
        row, reason = eligible(d)
        self.assertEqual(reason, "eligible")
        out = summarize([row], lambda r: r["heads"]["decisionProbability"])
        self.assertEqual(out["top1Rate"], 1)
        self.assertEqual(d, original)

    def test_postoff_unfrozen_and_tied_result_excluded(self):
        for change in ("time", "frozen", "tie"):
            d = detail()
            if change == "time": d["preRacePrediction"]["capturedAtEpoch"] = 1791640000
            if change == "frozen": d["preRacePrediction"]["frozen"] = False
            if change == "tie": d["result"]["finishers"][1]["finish"] = 1
            self.assertIsNone(eligible(d)[0])

    def test_final_odds_and_scores_never_become_features(self):
        a, _ = eligible(detail())
        d = detail()
        d["horses"] = [{"horseNumber": 1, "winOdds": 999, "integratedEvaluation": {"score": 99}}]
        b, _ = eligible(d)
        self.assertEqual(a["heads"], b["heads"])

    def test_invalid_probabilities_never_renormalized(self):
        for vals in ([.5, .6], [float('nan'), 1], [-.2, 1.2], [None, 1]):
            self.assertIsNone(probability_vector([{"p": v} for v in vals], "p"))
        self.assertIsNone(summarize([], lambda r: [])['logLoss'])


if __name__ == "__main__":
    unittest.main()
