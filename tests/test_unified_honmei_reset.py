"""Regression guard for the unified honmei on the isolated reset branch."""
from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

from arvexq.prediction.observed_model import apply_observed_marks
from tests.test_unified_jra_nar_observed_authority import race


class UnifiedHonmeiRegression(TestCase):
    def test_win_and_place_axis_are_same_horse(self):
        for circuit in ("中央", "地方"):
            with self.subTest(circuit=circuit):
                detail = apply_observed_marks(deepcopy(race(circuit)))
                marks = [
                    horse for horse in detail["horses"]
                    if horse.get("integratedEvaluation", {}).get("mark") == "◎"
                ]
                self.assertEqual(len(marks), 1)
                number = int(marks[0]["horseNumber"])
                decision = detail["honmeiDecision"]
                self.assertEqual(decision["horseNumber"], number)
                self.assertEqual(decision["axisHorseNumber"], number)
                self.assertEqual(decision["role"], "win-axis")
                self.assertEqual(
                    marks[0]["integratedEvaluation"]["honmeiRole"], "win-axis"
                )
                self.assertEqual(
                    sum(bool(h.get("integratedEvaluation", {}).get("podiumAxisEligible"))
                        for h in detail["horses"]), 1
                )
