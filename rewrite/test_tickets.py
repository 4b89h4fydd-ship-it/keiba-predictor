"""Tests for ticket generation and the EV honesty gates."""
import unittest

from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.tickets import TicketPolicy, generate_tickets
from rewrite.data.normalize import normalize_race
from rewrite.test_analysis import CLOSER_RUNS, FRONT_RUNS, MID_RUNS, SUMMARY, horse


def make_forecast():
    summary = dict(SUMMARY)
    race = normalize_race(summary, {"horses": [
        horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS), horse(3, MID_RUNS),
        horse(4, FRONT_RUNS), horse(5, MID_RUNS),
    ]}, "test://x")
    return forecast_race(race)


class TicketTests(unittest.TestCase):
    def setUp(self):
        self.forecast = make_forecast()
        self.odds = {1: 3.0, 2: 8.0, 3: 20.0, 4: 4.0, 5: 15.0}

    def test_probability_tickets_cover_kinds_with_caps(self):
        plan = generate_tickets(self.forecast, self.odds, calibration_validated=False)
        kinds = {t.kind for t in plan.probability_tickets}
        self.assertIn("win", kinds)
        self.assertIn("trio", kinds)
        policy = TicketPolicy()
        for kind in kinds:
            count = sum(1 for t in plan.probability_tickets if t.kind == kind)
            self.assertLessEqual(count, policy.max_points[kind])
        for t in plan.probability_tickets:
            self.assertGreater(t.probability, 0)

    def test_ev_suppressed_until_calibration_validated(self):
        plan = generate_tickets(self.forecast, self.odds, calibration_validated=False)
        self.assertEqual(plan.ev_tickets, ())
        self.assertEqual(plan.suppressed.get("ev_win"), "calibration-not-validated")

    def test_win_ev_estimates_match_probability_times_real_odds(self):
        plan = generate_tickets(self.forecast, self.odds, calibration_validated=False)
        # The EV ticket lane stays suppressed, but display estimates
        # exist for every runner with real win odds.
        self.assertEqual(plan.ev_tickets, ())
        estimates = {t.selection[0]: t for t in plan.win_ev_estimates}
        self.assertEqual(set(estimates), set(self.odds))
        for runner in self.forecast.runners:
            ticket = estimates[runner.number]
            self.assertEqual(ticket.lane, "ev-estimate")
            self.assertEqual(ticket.odds_status, "actual")
            self.assertIsNone(ticket.stake_units)
            self.assertAlmostEqual(
                ticket.expected_return,
                round(runner.p_win * self.odds[runner.number], 4),
                places=6,
            )
        # Sorted by expected value, highest first.
        values = [t.expected_return for t in plan.win_ev_estimates]
        self.assertEqual(values, sorted(values, reverse=True))
        # No real odds -> no estimates, nothing invented.
        empty = generate_tickets(self.forecast, {}, calibration_validated=False)
        self.assertEqual(empty.win_ev_estimates, ())
        # Partial odds -> estimates only for those horses.
        partial = generate_tickets(self.forecast, {2: 8.0},
                                    calibration_validated=False)
        self.assertEqual([t.selection for t in partial.win_ev_estimates], [(2,)])

    def test_non_win_ev_marked_odds_unavailable(self):
        plan = generate_tickets(self.forecast, self.odds, calibration_validated=True)
        for t in plan.probability_tickets:
            if t.kind != "win":
                self.assertEqual(t.odds_status, "unavailable")
                self.assertIsNone(t.expected_return)

    def test_ev_computed_only_with_real_odds_and_validation(self):
        plan = generate_tickets(self.forecast, {}, calibration_validated=True)
        self.assertEqual(plan.ev_tickets, ())
        plan2 = generate_tickets(self.forecast, self.odds, calibration_validated=True)
        for t in plan2.ev_tickets:
            self.assertEqual(t.kind, "win")
            self.assertGreater(t.expected_return, 1.0)
            self.assertIsNotNone(t.stake_units)

    def test_insufficient_forecast_yields_empty_plan(self):
        summary = dict(SUMMARY, title="2歳初出走")
        race = normalize_race(summary, {"horses": [horse(1, []), horse(2, [])]}, "t")
        plan = generate_tickets(forecast_race(race), self.odds,
                                 calibration_validated=True)
        self.assertEqual(plan.probability_tickets, ())
        self.assertEqual(plan.ev_tickets, ())


if __name__ == "__main__":
    unittest.main()
