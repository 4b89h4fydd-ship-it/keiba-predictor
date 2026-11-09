"""Contract tests for user-requested 18-section forecast audit."""
import unittest

from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.pace import forecast_pace
from rewrite.analysis.master18 import RUBRIC, analyze_master18
from rewrite.test_analysis import CLOSER_RUNS, FRONT_RUNS, MID_RUNS, horse, race_with


def fixture(*, scratched=False):
    horses = [
        horse(1, FRONT_RUNS, winOdds=2.0),
        horse(2, CLOSER_RUNS, winOdds=7.0),
        horse(3, MID_RUNS, winOdds=3.0),
        horse(4, FRONT_RUNS, winOdds=11.0),
        horse(5, MID_RUNS, winOdds=20.0, scratched=scratched),
    ]
    race = race_with(horses)
    f = forecast_race(race)
    return race, f, forecast_pace(race)


class Master18Tests(unittest.TestCase):
    def test_rubric_sums_to_one_hundred(self):
        self.assertEqual(sum(total for total, _ in RUBRIC.values()), 100)
        for total, parts in RUBRIC.values():
            self.assertLessEqual(sum(parts.values()), total)

    def test_all_runners_and_probability_identity(self):
        race, f, pace = fixture()
        data = analyze_master18(race, f, pace)
        self.assertEqual(data["version"], "master18-candidate-v1")
        self.assertEqual(len(data["allRunners"]), 5)
        self.assertEqual(data["top3Ranking"],
            [r.number for r in sorted(f.runners, key=lambda x: (-x.p_top3, x.number))])
        by_number = {r.number: r for r in f.runners}
        for c in data["allRunners"]:
            r = by_number[c["number"]]
            self.assertEqual(c["winProbability"], r.p_win)
            self.assertEqual(c["top3Probability"], r.p_top3)
            self.assertLessEqual(c["observedPoints"], c["possibleObserved"])
            self.assertEqual(c["range"][1] - c["range"][0],
                             100 - c["possibleObserved"])
            self.assertEqual(c["maximum"], 100)
            self.assertEqual(c["categories"]["trainingCondition"]["earned"], 0)
            self.assertEqual(c["categories"]["trainingCondition"]["status"], "missing")

    def test_scenarios_and_break_even_are_not_claimed_as_calibrated(self):
        race, f, pace = fixture()
        data = analyze_master18(race, f, pace)
        self.assertIsNone(data["paceSensitivity"]["scenarioFrequencies"])
        self.assertEqual(set(data["paceSensitivity"]["rankings"]),
                         {"slow", "normal", "fast"})
        self.assertEqual(len(data["paceSensitivity"]["stages"]), 4)
        tickets = data["tickets"]
        self.assertEqual(tickets["decision"], "見送り")
        self.assertIsNone(tickets["stakeAdvice"])
        self.assertEqual(len(tickets["profiles"]), 3)
        hit = tickets["profiles"][0]["candidate"]
        self.assertIsNotNone(hit)
        self.assertIn(hit["kind"], {"複勝", "ワイド"})
        self.assertGreater(hit["probabilityEstimate"], 0)
        self.assertIsNone(hit["actualOdds"])
        self.assertIsNone(hit["expectedReturn"])

    def test_incomplete_odds_never_invented(self):
        race = race_with([horse(1, FRONT_RUNS, winOdds=None),
                          horse(2, CLOSER_RUNS, winOdds=7),
                          horse(3, MID_RUNS, winOdds=3)])
        data = analyze_master18(race, forecast_race(race), forecast_pace(race))
        self.assertEqual(data["marketComparison"]["status"], "incomplete")
        self.assertEqual(data["tickets"]["outsiderNumbers"], [])
        self.assertIsNone(data["tickets"]["profiles"][1]["candidate"])

    def test_scratched_horse_is_not_ranked_or_wagered(self):
        race, f, pace = fixture(scratched=True)
        data = analyze_master18(race, f, pace)
        self.assertEqual(len(data["allRunners"]), 5)
        self.assertEqual(len(data["top3Ranking"]), 4)
        self.assertEqual(data["allRunners"][-1]["status"], "scratched")
        for item in data["tickets"]["profiles"]:
            if item["candidate"]:
                self.assertNotIn(5, item["candidate"]["numbers"])

    def test_race_identity_mismatch_fails_closed(self):
        race, f, pace = fixture()
        other = race_with([horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
                           horse(3, MID_RUNS)], race_id="another")
        with self.assertRaises(ValueError):
            analyze_master18(other, f, pace)

    def test_future_results_excluded_by_normalizer(self):
        future = {"date": "2026-10-29", "track": "名古屋", "distance": 1500,
                  "finish": 1, "fieldSize": 10}
        race = race_with([horse(1, FRONT_RUNS + [future]),
                          horse(2, CLOSER_RUNS), horse(3, MID_RUNS)])
        data = analyze_master18(race, forecast_race(race), forecast_pace(race))
        by_number = {c["number"]: c for c in data["allRunners"]}
        self.assertEqual(by_number[1]["rejectedFutureRuns"], 1)

    def test_no_claimed_percent_score_when_all_history_missing(self):
        race = race_with([horse(1, []), horse(2, []), horse(3, [])],
                         title="新馬")
        f = forecast_race(race)
        data = analyze_master18(race, f, forecast_pace(race))
        self.assertTrue(all(c["possibleObserved"] <= 10
                            for c in data["allRunners"]))
        self.assertEqual(data["tickets"]["decision"], "見送り")


if __name__ == "__main__":
    unittest.main()
