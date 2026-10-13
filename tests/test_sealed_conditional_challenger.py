"""Offline tests for the authentic-preoff-head conditional race challenger."""
import math
import unittest

from scripts.arvexq_sealed_conditional_challenger import (
    _extract, experiment, fit, predict,
)


def race(date, num, winner, heads, *, captured=100):
    horses = []
    for i in range(3):
        horses.append({"horseNumber": i + 1, "mark": "◎" if i == 0 else "",
                       "decisionProbability": heads["decision"][i],
                       "p1Probability": heads["p1"][i],
                       "p2Probability": heads["p2"][i],
                       "p3Probability": heads["p3"][i]})
    finish = [winner] + [x for x in (1, 2, 3) if x != winner]
    return {"date": date, "id": f"race-{date}-{num}",
            "startTime": "15:00", "circuit": "nar",
            "preRacePrediction": {
                "frozen": True, "raceId": f"race-{date}-{num}",
                "raceDate": date, "capturedAtEpoch": captured,
                "horses": horses},
            "result": {"status": "確定", "finishers": [
                {"horseNumber": no, "finish": rank}
                for rank, no in enumerate(finish, 1)]}}


class SealedChallengerTests(unittest.TestCase):
    def setUp(self):
        self.heads = {"decision": [.34, .33, .33],
                      "p1": [.55, .25, .20],
                      "p2": [.20, .60, .20],
                      "p3": [.15, .20, .65]}

    def test_no_future_or_unsealed_predictions(self):
        d = race("2026-10-07", 1, 1, self.heads)
        bad = race("2026-10-07", 2, 2, self.heads)
        bad["preRacePrediction"]["frozen"] = False
        postoff = race("2026-10-07", 3, 3, self.heads, captured=1_900_000_000)
        rows, exclusions, _, seen = _extract([("fixture", {"details": [d, bad, postoff]})])
        self.assertEqual((len(rows), seen), (1, 3))
        self.assertIn("missing-authentic-frozen-lock", exclusions)

    def test_probabilities_sum_to_one_and_no_labels_in_predictor(self):
        d = race("2026-10-07", 1, 1, self.heads)
        row, _, _, _ = _extract([("x", {"details": [d]})])
        a = predict(row[0], (.2, -.1, .03))
        d["result"]["finishers"][0]["horseNumber"] = 3
        b = predict(row[0], (.2, -.1, .03))
        self.assertEqual(a, b)
        self.assertTrue(all(math.isfinite(v) and v > 0 for v in a))
        self.assertAlmostEqual(sum(a), 1)

    def test_train_and_validation_holdout_separated(self):
        payloads = []
        from datetime import date, timedelta
        start = date(2026, 10, 7)
        for j in range(7):
            day = (start + timedelta(days=j)).isoformat()
            payloads.append((day, {"details": [
                race(day, k, 1 if k % 3 else 2, self.heads)
                for k in range(20)]}))
        report = experiment(payloads)
        self.assertEqual(report["status"], "exploratory-evaluated")
        self.assertEqual(report["split"]["test"]["count"], 40)
        self.assertEqual(report["productionPromoted"], False)
        self.assertTrue(all(math.isfinite(v) for v in
                            report["chosenOnValidationOnly"]["theta"]))

    def test_invalid_probability_rejected(self):
        heads = {**self.heads, "p3": [0.9, 0.9, 0.9]}
        r, excluded, _, _ = _extract([("x", {"details": [
            race("2026-10-07", 1, 1, heads)]})])
        self.assertEqual(len(r), 0)
        self.assertEqual(excluded["incomplete-original-heads"], 1)


if __name__ == "__main__":
    unittest.main()
