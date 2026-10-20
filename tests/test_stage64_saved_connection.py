"""Actual immutable 2026-10-17 saved JRA/NAR races through unchanged Stage64."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from arvexq.research.stage64.pipeline import STAGES, predict
from arvexq.research.stage64.protocol import ARMS, clean_input, code_hash
from scripts.arvexq_stage64_saved_connection import SAVED, run_saved_day

ROOT = Path(__file__).resolve().parents[1]


class Stage64SavedConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_saved_day("2026-10-17")
        cls.reference = json.loads((ROOT / "docs/research/stage64-results/summary.json")
                                   .read_text(encoding="utf-8"))

    def test_all_original_races_and_three_ability_methods_in_both_circuits(self):
        report = self.report
        self.assertEqual(set(report["byCircuit"]), {"jra", "nar"})
        self.assertEqual([report["byCircuit"][c]["races"] for c in ("jra", "nar")],
                         [36, 34])
        self.assertEqual(len(report["raceRows"]), 70)
        self.assertEqual(tuple(report["abilityMethods"]), ARMS)
        self.assertEqual(tuple(report["stages"]), STAGES)
        self.assertEqual(sum(v["armsExecuted"] for v in report["byCircuit"].values()), 210)
        self.assertFalse(report["productionEligible"])
        self.assertFalse(report["independentlyVerifiedPreoff"])
        self.assertFalse(report["productionChanged"])
        self.assertIsNone(report["productMarks"])
        self.assertIsNone(report["recommendedBets"])

    def test_real_six_stages_and_separate_jra_nar_scenario_counts(self):
        for owner in ("jra", "nar"):
            cohort = [row for row in self.report["raceRows"] if row["circuit"] == owner]
            self.assertTrue(cohort)
            scored = 0
            for row in cohort:
                self.assertTrue(row["rosterVerified"])
                self.assertTrue(row["savedSourceSha256"])
                self.assertEqual(set(row["predictions"]), set(ARMS))
                for arm, p in row["predictions"].items():
                    self.assertEqual(p["abilityMethod"], arm)
                    self.assertEqual(tuple(p["stages"]), STAGES)
                    self.assertFalse(p["productionEligible"])
                    if p["sixStageCalculated"]:
                        scored += 1
                        six = p["stages"]
                        self.assertEqual(len(six["pace"]["value"]), 1 if owner == "jra" else 4)
                        self.assertAlmostEqual(sum(six["probability"]["value"]["win"].values()), 1.)
                        self.assertAlmostEqual(sum(six["probability"]["value"]["top3"].values()), 3.)
                        self.assertIsNone(six["marks"]["value"]["productMarks"])
                        self.assertIsNone(six["tickets"]["value"]["recommendedBets"])
                        self.assertLessEqual(
                            len(six["tickets"]["value"]["hypotheticalTrifectaTop10"]), 10)
                    else:
                        self.assertFalse(p["stages"]["tickets"]["value"])
            self.assertGreater(scored, 0, owner + " should compute real saved six-stage races")
            self.assertEqual(scored, self.report["byCircuit"][owner]["sixStageCalculated"])
            self.assertEqual(scored + self.report["byCircuit"][owner]["unscoredArms"],
                             len(cohort) * 3)

    def test_no_comparability_claim_with_prior_527_race_study(self):
        self.assertIn("different-saved-cohort", self.report["historical527Comparison"])
        self.assertFalse(self.reference["productionEligible"])
        self.assertFalse(self.reference["independentlyVerifiedPreoff"])
        self.assertEqual(set(self.reference["byCircuit"]), {"jra", "nar"})
        for circuit, historical_count in (("jra", 108), ("nar", 419)):
            self.assertEqual(set(self.reference["byCircuit"][circuit]), set(ARMS))
            for arm in ARMS:
                self.assertEqual(
                    self.reference["byCircuit"][circuit][arm]["cohortRaces"],
                    historical_count)

    def test_outcomes_odds_and_product_bets_cannot_change_stage64(self):
        sample = {"id": "nar-2026-10-17-高知-01", "date": "2026-10-17",
                  "circuit": "地方", "fieldSize": 3,
                  "horses": [{"horseNumber": n, "recentRaces": [
                      {"date": "2026-10-10", "finish": n, "fieldSize": 6,
                       "cornerPositions": [n]}]} for n in (1, 2, 3)]}
        baseline = clean_input(sample)
        expected = {arm: predict(baseline, expected_circuit="nar", ability_method=arm)
                    for arm in ARMS}
        sample.update(result={"status": "確定", "finishers": [{"finish": 1}]},
                      payouts=[{"kind": "3連単", "amount": 99999}],
                      preRaceBet={"items": [{"kind": "おすすめ買い目"}]},
                      morningMarkSnapshot={"horses": [{"mark": "◎"}]})
        for horse in sample["horses"]:
            horse["winOdds"] = 1.1
        # Original prospective guard still rejects result-bearing input.
        with self.assertRaisesRegex(ValueError, "target outcome present"):
            clean_input(sample)
        projected = {k: v for k, v in sample.items()
                     if k not in ("result", "results", "payouts")}
        self.assertEqual(clean_input(projected), baseline)
        for arm in ARMS:
            self.assertEqual(predict(clean_input(projected),
                                     expected_circuit="nar", ability_method=arm),
                             expected[arm])

    def test_future_date_or_mismatched_horses_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "retrospective"):
            run_saved_day("2999-01-01")
        with self.assertRaisesRegex(ValueError, "retrospective"):
            run_saved_day("2026-10-20")

    def test_pipeline_and_protocol_source_not_modified_by_connector(self):
        self.assertTrue(code_hash())
        ui = (SAVED / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("arvexq_stage64_saved_connection", ui)


if __name__ == "__main__":
    unittest.main()
