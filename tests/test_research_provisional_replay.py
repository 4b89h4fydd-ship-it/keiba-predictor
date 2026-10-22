"""Read-only provisional mark evaluation: forecast first, label comparison second."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from scripts.arvexq_current_prediction_audit import evaluate_provisional_predictions


class ProvisionalReplayTests(TestCase):
    def test_chronological_mark_and_miss_diagnostics_without_postrace_leakage(self):
        def race(circuit, date, winner):
            return {"circuit": circuit, "date": date,
                    "id": circuit + "-" + date, "horses": [
                        {"horseNumber": 1, "allPastRuns": [
                            {"date": "2026-10-01", "fieldSize": 3, "finish": 1},
                            {"date": date, "fieldSize": 3, "finish": 1}]},
                        {"horseNumber": 2, "allPastRuns": [
                            {"date": "2026-10-01", "fieldSize": 3, "finish": 2}]}],
                    "result": {"status": "確定", "finishers": [
                        {"horseNumber": winner, "finish": 1},
                        {"horseNumber": 3-winner, "finish": 2}]}}
        first = race("地方", "2026-10-11", 1)
        second = race("地方", "2026-10-12", 2)
        originals = deepcopy([first, second])
        trained_on = []
        forecast_inputs = []

        def fit(history, *, circuit):
            trained_on.append((circuit, [x["id"] for x in history]))
            return {"dummy": True}

        def forecast(detail, model):
            forecast_inputs.append(detail)
            return {"predictionStatus": "candidate-analysis", "horses": [
                {"horseNumber": 1, "integratedEvaluation": {"mark": "◎"}},
                {"horseNumber": 2, "integratedEvaluation": {"mark": "○"}}],
                "scenarioAnalysis": {"reports": [
                    {"horseNumber": 1, "observedStarts": 1,
                     "featureValues": {"win_rate": 1}},
                    {"horseNumber": 2, "observedStarts": 1,
                     "featureValues": {"win_rate": 0}}]}}

        with patch("arvexq.prediction.learned_scenarios.fit_model", side_effect=fit), \
             patch("arvexq.prediction.new_forecast.build_forecast", side_effect=forecast):
            report = evaluate_provisional_predictions([second, first])

        local = report["地方"]
        self.assertEqual(local["noEarlierTrainedModel"], 1)
        self.assertEqual((local["scoredRaces"], local["winnerTop1Hits"]), (1, 0))
        self.assertEqual(local["misses"][0]["winner"], 2)
        self.assertEqual(local["misses"][0]["honmei"], 1)
        self.assertEqual(trained_on, [("地方", [first["id"]])])
        self.assertNotIn("result", forecast_inputs[0])
        self.assertEqual(len(forecast_inputs[0]["horses"][0]["allPastRuns"]), 1)
        self.assertEqual([first, second], originals)
        self.assertIsNone(report["中央"]["winnerTop1Rate"])


if __name__ == "__main__":
    import unittest
    unittest.main()
