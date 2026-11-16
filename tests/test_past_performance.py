"""Historic race-date-safe five-start feature regression."""
from __future__ import annotations
import unittest
from arvexq.prediction.past_performance import analyze_past_performance, observed_runs
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

    def test_normalized_history_retains_observed_weather_and_class(self):
        from arvexq.history import normalize_run, all_runs
        original = {**run("2026-09-20", 2), "weather": "雨", "className": "C2"}
        snapshot = dict(original)
        normalized = normalize_run(original)
        self.assertEqual(normalized["weather"], "雨")
        self.assertEqual(normalized["class"], "C2")
        self.assertEqual(original, snapshot)
        self.assertEqual(all_runs({"recentRaces": [original]})[0]["weather"], "雨")
        self.assertEqual(all_runs({"recentRaces": [original]})[0]["class"], "C2")
        self.assertEqual(normalize_run({"date": "2026-09-20"})["weather"], "")
        self.assertEqual(normalize_run({"date": "2026-09-20"})["class"], "")
        aliased = normalize_run({"date": "2026-09-20", "class_condition": "B2", "courseDirection": "右"})
        self.assertEqual(aliased["class"], "B2")
        self.assertEqual(aliased["direction"], "右")

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
            run("2026-09-07", 7, passing=[6, 6, 6, 6]),
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

    def test_candidate_full_career_does_not_mutate_preoff_original(self):
        from copy import deepcopy
        from arvexq.prediction.new_forecast import build_forecast
        from arvexq.prediction.learned_scenarios import fit_model
        horses = [
            {"horseNumber": i, "name": "候補馬", "recentRaces": [
                run("2026-09-27", i),
                run("2026-09-17", min(10, i + 1)),
                run("2026-09-07", min(10, i + 2)),
            ]} for i in range(1, 5)
        ]
        race = {**RACE, "id": "nar-candidate-test", "circuit": "地方", "horses": horses,
                "preRacePrediction": {"original": "sealed"},
                "preRaceBet": {"original": "ticket"}}
        original = deepcopy(race)
        training = deepcopy(race)
        training.update({"date": "2026-10-08", "id": "nar-training-test",
                         "result": {"status": "確定", "finishers": [
                             {"horseNumber": i, "finish": i} for i in range(1, 5)]}})
        model = fit_model([training], circuit="地方")
        candidate = build_forecast(race, model)
        self.assertEqual(race, original)
        self.assertEqual(candidate["preRacePrediction"], original["preRacePrediction"])
        self.assertEqual(candidate["preRaceBet"], original["preRaceBet"])
        self.assertEqual(candidate["predictionStatus"], "candidate-analysis")
        self.assertEqual(sum(h["integratedEvaluation"]["mark"] == "◎"
                             for h in candidate["horses"]), 1)
        self.assertNotIn("%", candidate["forecastText"])

    def test_stored_seconds_key_feeds_last3f_observed(self):
        # Regression (P2, 2026-11-16): stored details carry the closing
        # sectional as "last3fSeconds", never as "last3f". normalize_run did
        # not alias it, so last3fObserved was 0% in production while the raw
        # value existed on ~94% of runs.
        from arvexq.history import normalize_run
        stored = {"date": "2026-09-20", "track": "大井", "title": "Ｃ２",
                  "surface": "ダート", "distance": 1200, "condition": "良",
                  "fieldSize": 14, "finish": 2, "timeSeconds": 74.6,
                  "cornerPositions": [1, 1], "last3fSeconds": 39.3,
                  "marginSeconds": 0.4}
        self.assertEqual(normalize_run(stored)["last3f"], 39.3)
        self.assertEqual(normalize_run({"last600Seconds": 36.1})["last3f"], 36.1)
        self.assertEqual(normalize_run({"last3f": 35.0, "last3fSeconds": 39.3})["last3f"], 35.0)
        a = analyze_past_performance({"allPastRuns": [stored]}, RACE)
        self.assertEqual(a["datedRuns"], 1)
        self.assertEqual(a["last3fObservedRuns"], 1)
        self.assertTrue(a["runs"][0]["last3fObserved"])

    def test_jra_class_evidence_reaches_past_five_context(self):
        # Regression (P2, 2026-11-16): attach_jra_class_evidence existed but
        # was never called on the detail path, so opponentLevelObserved was
        # 0% even for JRA runs whose titles carry an explicit class.
        from arvexq.features.horse_features import attach_race_features
        jra_run = {"date": "2026-09-20", "track": "中山", "title": "3歳上1勝クラス",
                   "surface": "芝", "distance": 1200, "condition": "良",
                   "fieldSize": 10, "finish": 2, "cornerPositions": [3, 3],
                   "last3fSeconds": 34.5, "marginSeconds": 0.2}
        detail = {"date": "2026-10-09", "track": "中山", "surface": "芝",
                  "condition": "良", "distance": 1200, "circuit": "中央",
                  "horses": [{"horseNumber": 1, "allPastRuns": [dict(jra_run)]}]}
        attach_race_features(detail)
        past = detail["horseFeatures"][0]["pastPerformance"]
        self.assertEqual(past["opponentLevelObservedRuns"], 1)
        self.assertEqual(past["opponentLevelMean"], 2)  # 1勝クラス ordinal
        # NAR: no source-backed level exists in stored runs; nothing inferred.
        nar_detail = {"date": "2026-10-09", "track": "大井", "surface": "ダート",
                      "condition": "良", "distance": 1200, "circuit": "地方",
                      "horses": [{"horseNumber": 1, "allPastRuns": [
                          {**jra_run, "track": "大井", "title": "Ｃ２"}]}]}
        attach_race_features(nar_detail)
        nar_past = nar_detail["horseFeatures"][0]["pastPerformance"]
        self.assertEqual(nar_past["opponentLevelObservedRuns"], 0)
        self.assertIsNone(nar_past["opponentLevelMean"])

    def test_date_at_or_after_off_never_used(self):
        h = {"recentRaces": [run("2026-10-09", 1), run("2026-10-10", 1)]}
        self.assertEqual(analyze_past_performance(h, RACE)["datedRuns"], 0)
        self.assertEqual(analyze_past_performance(h, {"track": "大井"})["datedRuns"], 0)


if __name__ == "__main__":
    unittest.main()
