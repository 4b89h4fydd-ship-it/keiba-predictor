"""Tests for probability/marks forecast and calibration machinery."""
import unittest
from math import exp

from rewrite.analysis.calibration import (
    LabelledRace, fit_beta, log_loss, _check_split,
)
from rewrite.analysis.forecast import _assign_marks, forecast_race
from rewrite.data.normalize import normalize_race
from rewrite.test_analysis import CLOSER_RUNS, FRONT_RUNS, MID_RUNS, SUMMARY, horse


def race_with(horses, **overrides):
    summary = dict(SUMMARY)
    summary.update(overrides)
    return normalize_race(summary, {"horses": horses}, "test://x")


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.race = race_with([
            horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS), horse(3, MID_RUNS),
            horse(4, FRONT_RUNS), horse(5, MID_RUNS),
        ])
        self.forecast = forecast_race(self.race)
        self.by_number = {r.number: r for r in self.forecast.runners}

    def test_probabilities_sum_and_order(self):
        total = sum(r.p_win for r in self.forecast.runners if r.p_win is not None)
        self.assertAlmostEqual(total, 1.0, places=3)
        for r in self.forecast.runners:
            self.assertGreaterEqual(r.p_top3, r.p_top2)
            self.assertGreaterEqual(r.p_top2, r.p_win)

    def test_exactly_one_honmei_and_unique_marks(self):
        marks = [r.mark for r in self.forecast.runners if r.mark]
        self.assertEqual(marks.count("◎"), 1)
        self.assertEqual(len(marks), len(set(marks)))
        self.assertLessEqual(len(marks), 5)

    def test_status_is_honestly_uncalibrated(self):
        self.assertEqual(self.forecast.probability_status, "uncalibrated-prior")

    def test_unscored_runner_gets_floor_probability_not_zero(self):
        race = race_with([
            horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS), horse(3, MID_RUNS),
            horse(4, []),
        ])
        forecast = forecast_race(race)
        by_number = {r.number: r for r in forecast.runners}
        self.assertEqual(by_number[4].status, "unscored-floor-strength")
        self.assertIsNotNone(by_number[4].p_win)
        self.assertGreater(by_number[4].p_win, 0)
        self.assertLess(by_number[4].p_win, by_number[3].p_win)

    def test_debut_race_insufficient(self):
        race = race_with([horse(1, []), horse(2, [])], title="2歳初出走")
        forecast = forecast_race(race)
        self.assertEqual(forecast.status, "insufficient-scored-runners")
        self.assertTrue(all(r.mark == "" for r in forecast.runners))


class ExtendedMarkTests(unittest.TestCase):
    """Extended marks (2026-11-21): win ranks 6-8 at >= 2% win
    probability additionally receive 注, 穴, 伏 (cap eight marks)."""

    def _probs(self, wins):
        # (p_win, p_top2, p_top3) per horse number, top3 monotone
        # in the win order so ☆ lands on the fifth-ranked runner.
        return {n: (w, w * 1.5, min(0.95, w * 2.5))
                for n, w in enumerate(wins, start=1)}

    def test_rank6_above_threshold_gets_first_extended_mark(self):
        wins = [0.30, 0.20, 0.15, 0.10, 0.08, 0.021, 0.019, 0.017, 0.013]
        ranked = list(range(1, 10))
        marks = _assign_marks(ranked, self._probs(wins))
        self.assertEqual(marks[6], "注")
        self.assertNotIn(7, marks)  # 1.9% < 2%
        self.assertNotIn(8, marks)
        self.assertEqual(len(marks), 6)

    def test_all_extended_marks_and_cap_at_eight(self):
        wins = [0.25, 0.18, 0.14, 0.11, 0.09, 0.07, 0.05, 0.04, 0.03, 0.02]
        ranked = list(range(1, 11))
        marks = _assign_marks(ranked, self._probs(wins))
        self.assertEqual(marks[6], "注")
        self.assertEqual(marks[7], "穴")
        self.assertEqual(marks[8], "伏")
        self.assertNotIn(9, marks)  # rank 9 is out of range
        self.assertEqual(len(marks), 8)

    def test_exactly_at_threshold_qualifies(self):
        wins = [0.30, 0.20, 0.15, 0.10, 0.08, 0.02, 0.019, 0.018]
        ranked = list(range(1, 9))
        marks = _assign_marks(ranked, self._probs(wins))
        self.assertEqual(marks.get(6), "注")

    def test_star_inside_extended_range_is_not_double_marked(self):
        # ☆ (best top-3 among the rest) sits at win rank 7: rank 6
        # and rank 8 still receive the extended marks in order.
        wins = [0.30, 0.20, 0.15, 0.10, 0.08, 0.05, 0.04, 0.03]
        probs = self._probs(wins)
        probs[7] = (0.04, 0.10, 0.60)  # highest top-3 outside top 4
        ranked = list(range(1, 9))
        marks = _assign_marks(ranked, probs)
        self.assertEqual(marks[7], "☆")
        self.assertEqual(marks[6], "注")
        self.assertEqual(marks[8], "穴")
        self.assertEqual(len(marks), 7)


class CalibrationTests(unittest.TestCase):
    def test_time_split_guard(self):
        train = [LabelledRace("2026-10-02", {1: 0.5, 2: 0.5}, 1, (1,))]
        test = [LabelledRace("2026-10-01", {1: 0.5, 2: 0.5}, 1, (1,))]
        with self.assertRaises(ValueError):
            _check_split(train, test)

    def test_log_loss_rewards_better_probabilities(self):
        good = [LabelledRace("2026-10-01", {1: 0.9, 2: 0.1}, 1, (1,))]
        bad = [LabelledRace("2026-10-01", {1: 0.1, 2: 0.9}, 1, (1,))]
        self.assertLess(log_loss(good), log_loss(bad))

    def test_fit_beta_prefers_sharper_when_signal_is_real(self):
        # Synthetic: runner 1 always wins; strength_fn maps beta to a
        # distribution concentrated on runner 1 as beta grows.
        def strength_fn(beta, race):
            w = exp(beta)
            return {1: w / (w + 1), 2: 1 / (w + 1)}

        train = [LabelledRace("2026-10-01", {}, 1, (1,)) for _ in range(5)]
        test = [LabelledRace("2026-10-03", {}, 1, (1,)) for _ in range(3)]
        result = fit_beta(train, strength_fn, [0.1, 1.0, 3.0], test=test)
        self.assertEqual(result["beta"], 3.0)
        self.assertIn("test_log_loss", result)
        self.assertEqual(result["test_honmei"]["honmei_win_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
