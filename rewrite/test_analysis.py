"""Tests for ability + pace analysis (offline synthetic fixtures)."""
import unittest

from rewrite.analysis.ability import analyze_race
from rewrite.analysis.pace import forecast_pace
from rewrite.data.normalize import normalize_race


def run(date, corners, finish, behind=0.5):
    return {
        "date": date, "track": "名古屋", "distance": 1500, "surface": "ダート",
        "finish": finish, "fieldSize": 10, "cornerPositions": corners,
        "marginText": "", "timeSeconds": 98.0, "jockey": "騎手",
        "condition": "良", "weather": "晴", "timeBehindWinner": behind,
        "marginSeconds": behind, "carriedWeight": 56.0,
    }


def horse(number, runs, **overrides):
    base = {
        "horseNumber": number, "id": f"h{number}", "name": f"馬{number}",
        "frameNumber": number, "age": 4, "sex": "牡", "jockey": "騎手",
        "trainer": "調教師", "carriedWeight": 56.0, "bodyWeight": 480,
        "bodyWeightChange": 0, "winOdds": 5.0, "scratched": False,
        "allPastRuns": runs,
    }
    base.update(overrides)
    return base


SUMMARY = {
    "race_id": "nar-2026-10-28-名古屋-99", "race_date": "2026-10-28",
    "circuit": "地方", "track": "名古屋", "race_no": 99,
    "start_time": "12:20", "title": "テスト", "surface": "ダート",
    "distance": 1500, "weather": "晴", "condition": "良", "updated_at": 1,
}

FRONT_RUNS = [run("2026-10-01", [1, 1, 1, 1], 2), run("2026-09-01", [2, 1, 1, 1], 3)]
CLOSER_RUNS = [run("2026-10-01", [9, 8, 5, 3], 1, 0.0), run("2026-09-01", [10, 9, 6, 3], 2, 0.2)]
MID_RUNS = [run("2026-10-01", [5, 5, 5, 5], 5, 1.5), run("2026-09-01", [6, 5, 5, 5], 6, 1.8)]


def race_with(horses, **summary_overrides):
    summary = dict(SUMMARY)
    summary.update(summary_overrides)
    return normalize_race(summary, {"horses": horses}, "test://x")


class AbilityTests(unittest.TestCase):
    def test_closer_outscores_mid_and_scores_are_ranked(self):
        race = race_with([horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS), horse(3, MID_RUNS)])
        results = analyze_race(race)
        by_number = {r.number: r for r in results}
        self.assertIsNotNone(by_number[2].score)
        self.assertGreater(by_number[2].score, by_number[3].score)
        self.assertEqual(results[0].score, max(r.score for r in results))

    def test_no_runs_means_no_score(self):
        race = race_with([horse(1, []), horse(2, CLOSER_RUNS), horse(3, MID_RUNS)])
        by_number = {r.number: r for r in analyze_race(race)}
        self.assertIsNone(by_number[1].score)
        self.assertEqual(by_number[1].status, "insufficient-evidence")

    def test_debut_race_scores_nobody(self):
        race = race_with(
            [horse(1, []), horse(2, [])], title="2歳初出走"
        )
        self.assertTrue(all(r.score is None for r in analyze_race(race)))


class PaceTests(unittest.TestCase):
    def setUp(self):
        self.race = race_with([
            horse(1, FRONT_RUNS),
            horse(2, CLOSER_RUNS),
            horse(3, MID_RUNS),
            horse(4, [run("2026-10-01", [1, 2, 2, 2], 4), run("2026-09-01", [2, 2, 2, 2], 4)]),
            horse(5, [run("2026-10-01", [3, 3, 3, 3], 3), run("2026-09-01", [1, 3, 3, 3], 5)]),
        ])
        self.forecast = forecast_pace(self.race)

    def test_four_stages_present(self):
        self.assertEqual(
            tuple(self.forecast.stages.keys()), ("start", "corner3", "corner4", "straight")
        )

    def test_front_horse_leads_start_stage(self):
        first = self.forecast.stages["start"].order[0][0]
        self.assertIn(first, (1, 4, 5))

    def test_fast_scenario_helps_closer(self):
        normal_first = self.forecast.scenarios["normal"]["straight_order"].order[0][0]
        fast_order = [n for n, _ in self.forecast.scenarios["fast"]["straight_order"].order]
        self.assertLess(fast_order.index(2), 2)
        self.assertEqual(self.forecast.pace_label, "ハイペース想定")
        self.assertNotEqual(normal_first, None)

    def test_unknown_runner_reported_not_placed(self):
        race = race_with([horse(1, []), horse(2, CLOSER_RUNS)])
        forecast = forecast_pace(race)
        self.assertEqual(forecast.unknown_runners, (1,))
        placed = [n for n, _ in forecast.stages["start"].order]
        self.assertNotIn(1, placed)


if __name__ == "__main__":
    unittest.main()
