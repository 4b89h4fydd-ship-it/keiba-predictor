"""Contract tests for the 18-factor shadow engine (not accuracy claims)."""
import unittest
from math import isclose

from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.master_v1 import (
    CATEGORY_POINTS, MODEL_VERSION, PROBABILITY_STATUS, master_candidate,
)
from rewrite.analysis.tickets import generate_tickets
from rewrite.test_analysis import (
    CLOSER_RUNS, FRONT_RUNS, MID_RUNS, horse, race_with, run,
)


def sample_race():
    return race_with([
        horse(1, FRONT_RUNS, winOdds=2.1),
        horse(2, CLOSER_RUNS, winOdds=3.4),
        horse(3, MID_RUNS, winOdds=5.0),
        horse(4, FRONT_RUNS, winOdds=7.0),
        horse(5, MID_RUNS, winOdds=12.0),
    ])


class MasterCandidateTests(unittest.TestCase):
    def test_points_coverage_and_all_horses(self):
        race = sample_race()
        result, audit = master_candidate(race, forecast_race(race))
        self.assertEqual(audit["version"], MODEL_VERSION)
        self.assertEqual(sum(CATEGORY_POINTS.values()), 100)
        self.assertEqual(audit["status"], "shadow-candidate")
        self.assertEqual(len(audit["runners"]), 5)
        for row in audit["runners"]:
            self.assertEqual(sum(v["maximum"] for v in row["categories"].values()), 100)
            self.assertIsNone(row["categories"]["training_condition"]["earned"])
            self.assertIsNone(row["categories"]["gate"]["earned"])
            self.assertEqual(row["coveragePoints"], sum(
                item["maximum"] for item in row["categories"].values()
                if item["earned"] is not None))
            self.assertGreaterEqual(row["score100"], 0)
            self.assertLessEqual(row["score100"], 100)
        self.assertEqual(result.probability_status, PROBABILITY_STATUS)
        self.assertFalse(audit["validated"])

    def test_exact_pl_probabilities_marks_and_r24_tickets(self):
        race = sample_race()
        result, audit = master_candidate(race, forecast_race(race))
        self.assertTrue(isclose(sum(r.p_win for r in result.runners), 1.0, abs_tol=1e-10))
        self.assertTrue(isclose(sum(r.p_top3 for r in result.runners), 3.0, abs_tol=1e-10))
        self.assertEqual({r.mark for r in result.runners}, {"◎", "○", "▲", "△", "☆"})
        for row in result.runners:
            self.assertTrue(0 < row.p_win <= row.p_top2 <= row.p_top3 <= 1)
        ticket_plan = generate_tickets(result, {}, calibration_validated=False,
                                       trifecta_formation="R24")
        self.assertEqual(len([t for t in ticket_plan.probability_tickets
                              if t.kind == "trifecta"]), 24)
        self.assertEqual(ticket_plan.ev_tickets, ())
        self.assertEqual(set(audit["pace"]["scenarioOrder"]), {"slow", "normal", "fast"})
        self.assertIsNone(audit["pace"]["scenarioProbabilities"])

    def test_missing_data_never_imputed(self):
        race = race_with([
            horse(1, FRONT_RUNS, winOdds=2.2),
            horse(2, CLOSER_RUNS, winOdds=3.4),
            horse(3, MID_RUNS, winOdds=5.0),
            horse(4, [], winOdds=None),
            horse(5, FRONT_RUNS, winOdds=7.0),
            horse(6, CLOSER_RUNS, scratched=True),
        ])
        result, audit = master_candidate(race, forecast_race(race))
        self.assertEqual(len(audit["runners"]), 5)
        self.assertEqual(audit["marketStatus"], "unavailable")
        self.assertFalse(any(r["valueHypothesis"] for r in audit["runners"]))
        unscored = next(r for r in audit["runners"] if r["horseNumber"] == 4)
        self.assertIsNone(unscored["score100"])
        self.assertEqual(unscored["coveragePoints"], 0)
        self.assertGreater(next(r.p_win for r in result.runners if r.number == 4), 0)

    def test_future_history_cannot_enter_assessment(self):
        race = race_with([
            horse(1, [run("2026-12-01", [1, 1, 1, 1], 1)]),
            horse(2, FRONT_RUNS), horse(3, CLOSER_RUNS), horse(4, MID_RUNS),
        ])
        self.assertEqual(race.active_runners[0].rejected_future_runs, 1)
        _, audit = master_candidate(race, forecast_race(race))
        unscored = next(r for r in audit["runners"] if r["horseNumber"] == 1)
        self.assertIsNone(unscored["score100"])

    def test_mismatched_race_rejected(self):
        from rewrite.analysis.forecast import RaceForecast
        race = sample_race()
        baseline = forecast_race(race)
        wrong = RaceForecast("bad-id", baseline.beta, baseline.probability_status,
                             baseline.runners, baseline.status)
        with self.assertRaisesRegex(ValueError, "identity"):
            master_candidate(race, wrong)

    def test_insufficient_debut_passes_through(self):
        race = race_with([horse(1, []), horse(2, []), horse(3, [])], title="2歳初出走")
        incumbent = forecast_race(race)
        result, audit = master_candidate(race, incumbent)
        self.assertEqual(result, incumbent)
        self.assertEqual(audit["status"], "insufficient-incumbent")
        self.assertTrue(all(r["score100"] is None for r in audit["runners"]))


if __name__ == "__main__":
    unittest.main()
