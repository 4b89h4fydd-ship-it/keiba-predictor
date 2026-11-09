"""Safety and calculation invariants for the 18-section master shadow engine."""
from __future__ import annotations

import unittest

from rewrite.analysis.master_v1 import SCORE_WEIGHTS, forecast_master
from rewrite.data.normalize import normalize_race
from rewrite.test_analysis import (
    CLOSER_RUNS, FRONT_RUNS, MID_RUNS, SUMMARY, horse, run,
)


def fixture(*, title="テスト", circuit="地方", odds=None, future=False,
            scratched=None):
    horses = [
        horse(1, FRONT_RUNS),
        horse(2, CLOSER_RUNS),
        horse(3, MID_RUNS),
        horse(4, [run("2026-10-01", [1, 1, 2, 2], 4, 0.7)]),
        horse(5, [run("2026-10-01", [4, 4, 4, 4], 3, 0.8)]),
    ]
    if odds is not None:
        for h, o in zip(horses, odds):
            h["winOdds"] = o
    if future:
        horses[0]["allPastRuns"] = [
            run("2026-10-29", [1, 1, 1, 1], 1, 0.0)
        ] + horses[0]["allPastRuns"]
    if scratched:
        horses[scratched - 1]["scratched"] = True
    summary = dict(SUMMARY, title=title, circuit=circuit)
    return normalize_race(summary, {"horses": horses}, "test://preoff")


class MasterForecastTests(unittest.TestCase):
    def test_weights_total_100_but_score_is_not_win_probability(self):
        self.assertEqual(sum(SCORE_WEIGHTS.values()), 100)
        result = forecast_master(fixture())
        self.assertEqual(result["status"], "unvalidated-prior")
        self.assertEqual(result["probabilityModel"]["heldOutCalibration"], False)
        self.assertTrue(all(r["score100"] is not None for r in result["rows"]))
        self.assertTrue(all(r["score100"] != r["winProbability"]
                            for r in result["rows"]))

    def test_probability_mass_and_nesting_for_all_horses(self):
        result = forecast_master(fixture())
        rows = result["rows"]
        self.assertEqual(len(rows), 5)
        self.assertAlmostEqual(sum(r["winProbability"] for r in rows), 1, places=3)
        self.assertAlmostEqual(sum(r["top2Probability"] for r in rows), 2, places=3)
        self.assertAlmostEqual(sum(r["top3Probability"] for r in rows), 3, places=3)
        for r in rows:
            self.assertGreaterEqual(r["top3Probability"], r["top2Probability"])
            self.assertGreaterEqual(r["top2Probability"], r["winProbability"])
        self.assertEqual(len(set(r["mark"] for r in rows)), 5)

    def test_no_market_odds_in_ability_score_or_probabilities(self):
        low = forecast_master(fixture(odds=[1.5, 3, 5, 9, 20]))
        high = forecast_master(fixture(odds=[50, 22, 10, 2, 1.5]))
        self.assertEqual(
            [(r["horseNumber"], r["score100"], r["winProbability"])
             for r in low["rows"]],
            [(r["horseNumber"], r["score100"], r["winProbability"])
             for r in high["rows"]],
        )
        self.assertNotEqual(
            [(r["horseNumber"], r["marketRank"]) for r in low["rows"]],
            [(r["horseNumber"], r["marketRank"]) for r in high["rows"]],
        )

    def test_future_results_do_not_leak_into_forecast(self):
        clean = forecast_master(fixture())
        polluted = forecast_master(fixture(future=True))
        self.assertEqual(
            [(r["horseNumber"], r["score100"]) for r in clean["rows"]],
            [(r["horseNumber"], r["score100"]) for r in polluted["rows"]],
        )

    def test_three_scenarios_have_no_invented_likelihood(self):
        result = forecast_master(fixture())
        self.assertEqual(
            result["probabilityModel"]["scenarioLikelihoods"],
            {"slow": None, "normal": None, "fast": None},
        )
        self.assertEqual(
            set(result["pace"]["stages"]),
            {"start", "corner3", "corner4", "straight"},
        )
        for r in result["rows"]:
            lo, hi = r["top3ScenarioRange"]
            self.assertLessEqual(lo, r["top3Probability"])
            self.assertGreaterEqual(hi, r["top3Probability"])

    def test_purchase_is_suppressed_with_uncalibrated_probs(self):
        result = forecast_master(fixture())
        self.assertEqual(result["purchaseDecision"], "見送り")
        self.assertEqual(result["betCandidates"]["decision"], "見送り")
        self.assertTrue(result["betCandidates"]["hitFirst"])
        self.assertTrue(result["betCandidates"]["balanced"])
        for tickets in ("hitFirst", "balanced", "outsider"):
            for ticket in result["betCandidates"][tickets]:
                self.assertFalse(ticket["purchaseEligible"])
                self.assertIsNone(ticket["expectedReturn"])
                self.assertIsNone(ticket["quotedOdds"])
        self.assertEqual(
            sum(result["betCandidates"]["stakeFor1000Yen"].values()), 0
        )

    def test_unknown_history_has_no_fabricated_probabilities(self):
        race = normalize_race(
            SUMMARY,
            {"horses": [horse(1, FRONT_RUNS), horse(2, []),
                        horse(3, MID_RUNS), horse(4, [])]},
            "test://preoff",
        )
        result = forecast_master(race)
        self.assertEqual(result["status"], "insufficient-evidence")
        self.assertTrue(all(r["winProbability"] is None for r in result["rows"]))
        self.assertEqual(result["purchaseDecision"], "見送り")

    def test_debut_is_special_case_without_training_or_bloodline_data(self):
        race = normalize_race(
            dict(SUMMARY, title="2歳新馬", circuit="中央"),
            {"horses": [horse(1, []), horse(2, []), horse(3, []),
                        horse(4, [])]},
            "test://preoff",
        )
        result = forecast_master(race)
        self.assertEqual(result["segment"], "debut")
        self.assertEqual(result["status"], "insufficient-evidence")
        self.assertIsNone(result["honmeiNumber"])
        self.assertTrue(all(r["mark"] == "" for r in result["rows"]))

    def test_scratched_runner_excluded_from_probability_mass_and_tickets(self):
        result = forecast_master(fixture(scratched=5))
        active = [r for r in result["rows"] if r.get("rank") is not None]
        removed = [r for r in result["rows"] if r.get("status") == "scratched"]
        self.assertEqual([r["horseNumber"] for r in removed], [5])
        self.assertEqual(len(active), 4)
        self.assertAlmostEqual(sum(r["winProbability"] for r in active), 1, places=3)
        for group in ("hitFirst", "balanced", "outsider"):
            for ticket in result["betCandidates"][group]:
                self.assertNotIn(5, ticket["horseNumbers"])

    def test_banei_rejected_by_normalizer(self):
        with self.assertRaises(ValueError):
            normalize_race(dict(SUMMARY, track="帯広"), {"horses": []},
                           "test://preoff")

    def test_two_runner_race_cannot_assume_standard_top_three(self):
        race = normalize_race(
            SUMMARY, {"horses": [horse(1, FRONT_RUNS), horse(2, MID_RUNS)]},
            "test://preoff",
        )
        result = forecast_master(race)
        self.assertEqual(result["status"], "insufficient-active-roster")
        self.assertEqual(result["decision"], "見送り")


if __name__ == "__main__":
    unittest.main()
