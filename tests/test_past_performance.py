"""Historic race-date-safe five-start feature regression."""
from __future__ import annotations
import unittest
from arvexq.prediction.past_performance import analyze_past_performance, observed_runs
from arvexq.prediction.factor_model import collect_horse_raw_metrics
from arvexq.features.horse_features import build_horse_features


def run(date: str, finish: int, *, distance: int = 1200, surface: str = "ダート",
        passing=None, last3f=35.5, level=60):
    return {"date": date, "track": "大井", "title": "Race" + date, "surface": surface,
            "distance": distance, "condition": "良", "fieldSize": 10, "finish": finish,
            "cornerPositions": passing or [3, 3, 3, 3], "last3f": last3f,
            "last3fRank": 3, "opponentLevel": level,
            "margin": 0.4, "speedIndex": 78, "timeSeconds": 72.1}
RACE = {"date": "2026-10-09", "track": "大井", "surface": "ダート",
        "condition": "良", "distance": 1200}


class PastFiveContextTests(unittest.TestCase):
    def test_date_order_dedupe_and_future_exclusion(self):
        runs = [run("2026-09-01", 2), run("2026-10-10", 1),
                run("2026-09-20", 3), run("2026-08-01", 1),
                run("2026-09-20", 3), run("2026-07-01", 7),
                run("2026-06-01", 2), run("2026-05-01", 5)]
        d = {"recentRaces": runs, "allPastRuns": runs}
        recent = observed_runs(d, RACE)
        self.assertEqual(len(recent), 5)
        self.assertEqual([x["_raceDate"] for x in recent],
                         ["2026-09-20", "2026-09-01", "2026-08-01",
                          "2026-07-01", "2026-06-01"])
        analysis = analyze_past_performance(d, RACE)
        self.assertEqual(analysis["top3"], 4)
        self.assertEqual(analysis["comparableRuns"], 5)
        self.assertEqual(analysis["closingTop3Ranks"], 5)
        self.assertEqual(analysis["marginObservedRuns"], 5)
        features = build_horse_features({"horseNumber": 1, **d}, RACE)
        self.assertEqual(features["historySamples"], 5)
        self.assertEqual(features["pastPerformance"]["top3"], 4)
        raw = collect_horse_raw_metrics(d, RACE)
        self.assertIsNotNone(raw["record_recent_context"])
        self.assertIsNotNone(raw["suit_comparable_recent"])

    def test_not_comparable_is_not_claimed_to_be_bad_or_good(self):
        runs = [run("2026-09-20", 1, distance=1800),
                run("2026-09-18", 1, surface="芝"),
                run("2026-09-16", 1, distance=1400)]
        data = analyze_past_performance({"recentRaces": runs}, RACE)
        self.assertEqual(data["datedRuns"], 3)
        self.assertEqual(data["comparableRuns"], 0)
        self.assertIsNone(data["comparableQuality"])
        self.assertNotIn("same-surface-distance-no-podium", data["riskFlags"])

    def test_same_context_podium_failure_and_pace_fades_are_risk(self):
        h = {"recentRaces": [
            run("2026-09-27", 9, passing=[1, 1, 2, 2]),
            run("2026-09-17", 8, passing=[2, 2, 2, 3]),
            run("2026-09-07", 7, passing=[4, 4, 5, 5]),
        ]}
        a = analyze_past_performance(h, RACE)
        self.assertEqual(a["frontFadeCount"], 2)
        self.assertIn("repeated-front-fade", a["riskFlags"])
        self.assertIn("same-surface-distance-no-podium", a["riskFlags"])
        self.assertEqual(a["comparableTop3"], 0)

    def test_no_preoff_dates_means_unknown_not_zero_skill(self):
        horse = {"recentRaces": [{"fieldSize": 10, "finish": 1, "distance": 1200}]}
        context = analyze_past_performance(horse, RACE)
        self.assertEqual(context["datedRuns"], 0)
        self.assertIsNone(context["top3Rate"])
        self.assertEqual(context["status"], "missing-dated-past-runs")
        raw = collect_horse_raw_metrics(horse, RACE)
        self.assertIsNone(raw["record_recent_context"])
        self.assertIsNone(raw["pace_front_hold_recent"])

    def test_date_at_or_after_off_never_used(self):
        h = {"recentRaces": [run("2026-10-09", 1), run("2026-10-10", 1)]}
        self.assertEqual(analyze_past_performance(h, RACE)["datedRuns"], 0)
        self.assertEqual(analyze_past_performance(h, {"track": "大井"})["datedRuns"], 0)


if __name__ == "__main__":
    unittest.main()
