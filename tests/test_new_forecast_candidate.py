"""Candidate replacement smoke checks; does not change production authority."""
from __future__ import annotations
from copy import deepcopy
from unittest import TestCase
from arvexq.prediction.new_forecast import build_forecast, VERSION
from test_unified_jra_nar_observed_authority import race

class ReplacementForecastTests(TestCase):
    def test_both_circuits_preserve_input_and_produce_one_honmei(self):
        for circuit in ("中央", "地方"):
            with self.subTest(circuit=circuit):
                source = race(circuit)
                original = deepcopy(source)
                result = build_forecast(source)
                self.assertEqual(source, original)
                self.assertEqual(result["predictionModelVersion"], VERSION)
                self.assertEqual(result["predictionStatus"], "ready")
                marks = [h for h in result["horses"] if h["integratedEvaluation"]["mark"] == "◎"]
                self.assertEqual(len(marks), 1)
                self.assertEqual(result["honmeiDecision"]["horseNumber"], marks[0]["horseNumber"])
                self.assertEqual(result["honmeiDecision"]["axisHorseNumber"], marks[0]["horseNumber"])
                self.assertNotIn("%", result["forecastText"])
                self.assertNotIn("点", result["forecastText"])
    def test_missing_history_is_not_promoted_to_prediction(self):
        detail = race("地方")
        detail["horses"][0]["recentRaces"] = []
        result = build_forecast(detail)
        self.assertNotEqual(result["predictionStatus"], "ready")
        self.assertFalse(any(h["integratedEvaluation"]["mark"] for h in result["horses"]))
    def test_original_archive_survives(self):
        detail = race("地方")
        detail["preRacePrediction"] = {"original": "unchanged"}
        detail["preRaceBet"] = {"original": "unchanged"}
        result = build_forecast(detail)
        self.assertEqual(result["preRacePrediction"], detail["preRacePrediction"])
        self.assertEqual(result["preRaceBet"], detail["preRaceBet"])
