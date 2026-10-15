"""Regression: scheduled D1 pre-off locks must use the actual NAR 60/40 model.

No JRA-only factorEvidence, P1/P2/P3 substitute input or result-time backfill.
"""
import copy
import unittest
from datetime import datetime
from unittest.mock import patch

from arvexq.prediction.nar_model import MODEL_VERSION, apply_nar_marks
from arvexq.prediction.prerace_archive import JST, sealed_lock
from scripts.arvexq_freeze_predictions import prepare_seal
from tests.test_nar_mineta_margin_authority import race


def local_card():
    detail = race()
    detail.update({
        "id": "nar-2099-01-10-園田-01",
        "date": "2099-01-10",
        "startTime": "23:00",
        "raceNumber": 1,
        "fieldSize": len(detail["horses"]),
    })
    return detail


class NarScheduledSealTests(unittest.TestCase):
    def test_complete_local_factors_create_genuine_frozen_prediction(self):
        detail = local_card()
        with patch("app._prediction_clock_state", return_value=("pre", 20)):
            outcome = prepare_seal(detail, now=datetime.now(JST))
        self.assertEqual(outcome["status"], "sealed", outcome)
        frozen = sealed_lock(outcome["detail"])
        self.assertIsNotNone(frozen)
        self.assertGreaterEqual(frozen["markCount"], 3)
        self.assertEqual(frozen["circuitMethod"], MODEL_VERSION)
        self.assertEqual(frozen["honmeiHorseNumber"],
                         next(z["horseNumber"] for z in frozen["horses"] if z["mark"] == "◎"))
        self.assertNotIn("preRacePrediction", detail)
        self.assertEqual(len(frozen["horses"]), len(detail["horses"]))
        for horse in outcome["detail"]["horses"]:
            evidence = horse["integratedEvaluation"]
            self.assertNotIn("factorEvidence", evidence)
            self.assertIn("narModelEvidence", evidence)
            self.assertEqual(evidence["markEngineVersion"], MODEL_VERSION)

    def test_local_missing_margin_is_not_replaced_with_fake_prediction(self):
        detail = local_card()
        for run in detail["horses"][-1]["recentRaces"]:
            run.pop("timeBehindWinner", None)
        with patch("app._prediction_clock_state", return_value=("pre", 20)):
            outcome = prepare_seal(detail, now=datetime.now(JST))
        self.assertEqual(outcome["status"], "incomplete-prediction", outcome)
        self.assertNotIn("preRacePrediction", detail)

    def test_jra_only_factor_evidence_cannot_be_a_nar_fallback(self):
        detail = local_card()
        for horse in detail["horses"]:
            horse["integratedEvaluation"] = {"factorEvidence": {
                "primaryPillarCoverage": 3}, "coreAbilityScore": 99,
                "mark": "◎"}
        with patch("app._prediction_clock_state", return_value=("pre", 20)):
            # Existing NAR scorer overwrites legacy evaluations; no second
            # ranking path gets a chance to invent a missing margin.
            outcome = prepare_seal(detail, now=datetime.now(JST))
        self.assertEqual(outcome["status"], "sealed", outcome)
        self.assertNotIn("factorEvidence",
                         outcome["detail"]["horses"][0]["integratedEvaluation"])


if __name__ == "__main__":
    unittest.main()
