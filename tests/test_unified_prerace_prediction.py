"""Real scheduled forecast regression after PR #180 unified JRA and NAR 60/40.

No obsolete three-factor gates, no unproven horse, and no post-off backfill.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from unittest import TestCase, main
from unittest.mock import patch

from arvexq.prediction.observed_model import JRA_MODEL_VERSION, NAR_MODEL_VERSION
from arvexq.prediction.prerace_archive import JST, sealed_lock
from scripts.arvexq_freeze_predictions import prepare_seal
from tests.test_unified_jra_nar_observed_authority import race


def complete_fixture(circuit):
    detail = race(circuit)
    detail["date"] = "2099-01-10"
    detail["id"] = ("jra-" if circuit == "中央" else "nar-") + "2099-01-10-test-01"
    detail["startTime"] = "23:00"
    detail["raceNumber"] = 1
    detail["fieldSize"] = len(detail["horses"])
    return detail


class UnifiedScheduledPredictionTests(TestCase):
    def test_both_circuits_create_archives_from_complete_6040_observations(self):
        for circuit, version in (("地方", NAR_MODEL_VERSION), ("中央", JRA_MODEL_VERSION)):
            with self.subTest(circuit=circuit):
                detail = complete_fixture(circuit)
                original = deepcopy(detail)
                with patch("app._prediction_clock_state", return_value=("pre", 20)):
                    result = prepare_seal(detail, now=datetime.now(JST))
                self.assertEqual(result["status"], "sealed", result)
                frozen = sealed_lock(result["detail"])
                self.assertIsNotNone(frozen)
                self.assertEqual(frozen["circuitMethod"], version)
                self.assertEqual(frozen["fieldSize"], len(original["horses"]))
                self.assertGreaterEqual(frozen["markCount"], 3)
                self.assertEqual(result["detail"]["observedModelCoverage"]["fullyObserved"],
                                 len(original["horses"]))
                self.assertEqual(result["detail"]["predictionStatus"], "ready")
                self.assertNotIn("preRacePrediction", detail)
                self.assertEqual(original["horses"], detail["horses"])
                for horse in result["detail"]["horses"]:
                    e = horse["integratedEvaluation"]
                    self.assertNotIn("factorEvidence", e)
                    self.assertIn("narModelEvidence", e)
                    self.assertEqual(e["markEngineVersion"], version)

    def test_missing_real_margin_never_becomes_a_frozen_forecast(self):
        for circuit in ("地方", "中央"):
            with self.subTest(circuit=circuit):
                detail = complete_fixture(circuit)
                for run in detail["horses"][-1]["recentRaces"]:
                    if circuit == "地方":
                        run.pop("marginSeconds", None)
                    else:
                        run.pop("marginEvidence", None)
                with patch("app._prediction_clock_state", return_value=("pre", 20)):
                    result = prepare_seal(detail, now=datetime.now(JST))
                self.assertEqual(result["status"], "incomplete-prediction", result)
                self.assertFalse(detail.get("preRacePrediction"))

    def test_no_retrospective_forecast_even_with_complete_model(self):
        detail = complete_fixture("地方")
        result = prepare_seal(detail, now=datetime(2099, 1, 10, 23, 1, tzinfo=JST))
        self.assertEqual(result["status"], "started-no-new-lock")
        self.assertNotIn("preRacePrediction", detail)


if __name__ == "__main__":
    main()
