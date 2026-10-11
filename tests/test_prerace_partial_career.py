"""Only well-observed near-complete fields may produce a pre-off provisional seal."""
import copy
import unittest
from datetime import datetime, timedelta

from arvexq.prediction.prerace_archive import JST
from arvexq.prediction.career_readiness import assess_career_readiness
from arvexq.prediction.final_marks import (
    apply_core_marks, sufficiently_observed_partial_career,
)
from scripts.arvexq_freeze_predictions import prepare_seal


NOW = datetime(2026, 10, 13, 12, 0, tzinfo=JST)


def race(count=15, verified=13):
    date = NOW.strftime("%Y-%m-%d")
    horses = []
    for no in range(1, count + 1):
        runs = [
            {"date": f"2026-09-{5 + i * 5:02d}", "track": "東京",
             "distance": 1800, "fieldSize": 12, "finish": (no + i) % 8 + 1,
             "timeSeconds": 110.4 + (no % 7) * .7}
            for i in range(3)
        ]
        horses.append({
            "horseNumber": no, "name": f"Horse-{no}", "jockey": f"J-{no}",
            "recentRaces": copy.deepcopy(runs), "allPastRuns": copy.deepcopy(runs),
            "_careerHistoryAudit": {
                "version": "arvexq-career-coverage-v1",
                "requestedAtRaceDate": date, "reportedStarts": 3 if no <= verified else 4,
                "observedRuns": 3, "complete": no <= verified,
                "paginationComplete": True, "reportedStartsSource": "fixture",
                "failedProviders": [],
            },
        })
    return {"id": f"jra-{date}-東京-11", "date": date,
            "circuit": "中央", "track": "東京", "raceNumber": 11,
            "startTime": "12:30", "fieldSize": count, "surface": "芝",
            "distance": 1800, "horses": horses}


def model(working):
    return {
        "raceId": working["id"], "raceDate": working["date"],
        "capturedAtEpoch": int(NOW.timestamp()), "markCount": 3,
        "horses": [
            {"horseNumber": h["horseNumber"],
             "mark": (h.get("integratedEvaluation") or {}).get("mark", "")}
            for h in working["horses"]
        ],
    }


class PartialCareerSealTests(unittest.TestCase):
    def test_thirteen_of_fifteen_with_observed_missing_horses(self):
        detail = race()
        ready = assess_career_readiness(detail)
        self.assertFalse(ready["ready"])
        self.assertEqual(ready["completeHorses"], 13)
        self.assertTrue(sufficiently_observed_partial_career(detail, ready))
        forecast = apply_core_marks(copy.deepcopy(detail))
        self.assertEqual(forecast["predictionStatus"], "partial-career-evidence")
        self.assertFalse(forecast["careerReadiness"]["ready"])
        result = prepare_seal(detail, now=NOW, assign=apply_core_marks, build=model)
        self.assertEqual(result["status"], "sealed", result)
        original = result["detail"]["preRacePrediction"]
        self.assertFalse(original["careerEvidence"]["fullCareerVerified"])
        self.assertEqual(len(original["careerEvidence"]["blockedHorses"]), 2)
        self.assertFalse(detail.get("preRacePrediction"), "input cannot be mutated")

    def test_many_unverified_do_not_seal(self):
        detail = race(count=14, verified=0)
        readiness = assess_career_readiness(detail)
        self.assertFalse(sufficiently_observed_partial_career(detail, readiness))
        forecast = apply_core_marks(copy.deepcopy(detail))
        self.assertEqual(forecast["predictionStatus"], "waiting-for-full-career")
        result = prepare_seal(detail, now=NOW, assign=apply_core_marks,
                              build=lambda _: self.fail("unverified field cannot be sealed"))
        self.assertEqual(result["status"], "waiting-for-full-career")

    def test_three_race_minimum_and_no_future_bypass(self):
        detail = race()
        for h in detail["horses"][-2:]:
            h["recentRaces"] = h["recentRaces"][:2]
            h["allPastRuns"] = h["allPastRuns"][:2]
        readiness = assess_career_readiness(detail)
        self.assertFalse(sufficiently_observed_partial_career(detail, readiness))
        self.assertEqual(prepare_seal(detail, now=NOW, assign=apply_core_marks,
                                      build=lambda _: self.fail("insufficient history"))["status"],
                         "waiting-for-full-career")
        future = race()
        for h in future["horses"][-2:]:
            h["recentRaces"] = [{"date": "2026-10-14", "finish": 1, "fieldSize": 12}]
            h["allPastRuns"] = h["recentRaces"]
        self.assertFalse(sufficiently_observed_partial_career(
            future, assess_career_readiness(future)))

    def test_post_off_never_creates_an_original(self):
        detail = race()
        result = prepare_seal(detail, now=NOW + timedelta(minutes=31),
                              assign=apply_core_marks, build=model)
        self.assertEqual(result["status"], "started-no-new-lock")


if __name__ == "__main__":
    unittest.main()
