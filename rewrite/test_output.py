"""Tests for the production-shape output adapter (offline fixtures)."""
import re
import unittest

from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.pace import forecast_pace
from rewrite.analysis.tickets import generate_tickets
from rewrite.data.normalize import normalize_race
from rewrite.output.api_shape import day_payload, model_hash, race_payload
from rewrite.test_analysis import (
    CLOSER_RUNS, FRONT_RUNS, MID_RUNS, SUMMARY, horse,
)

BETA = 2.0
PROVENANCE = {
    "snapshot_sha256": "a" * 64,
    "captured_at": "2026-10-28T01:00:00+09:00",
    "odds": [],
}
MARK_ORDER = ["◎", "○", "▲", "△", "☆"]


def build_race():
    return normalize_race(
        SUMMARY,
        {"horses": [
            horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS), horse(3, MID_RUNS),
            horse(4, FRONT_RUNS), horse(5, MID_RUNS),
        ]},
        "test://x",
    )


def build_payload(race=None, provenance=PROVENANCE):
    race = race or build_race()
    forecast = forecast_race(race, beta=BETA)
    pace = forecast_pace(race)
    odds = {
        r.number: r.win_odds.value for r in race.runners if r.win_odds.present
    }
    tickets = generate_tickets(forecast, odds, calibration_validated=False)
    return race_payload(race, forecast, pace, tickets, provenance=provenance)


class DayPayloadTests(unittest.TestCase):
    def test_day_shape(self):
        race = build_race()
        payload = day_payload("2026-10-28", [race])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["date"], "2026-10-28")
        self.assertEqual(payload["raceCount"], 1)
        row = payload["races"][0]
        for key in ("id", "date", "circuit", "track", "raceNumber",
                    "startTime", "title", "surface", "distance",
                    "weather", "condition", "raceStatus", "updatedAtEpoch"):
            self.assertIn(key, row)
        self.assertEqual(row["id"], race.race_id)
        self.assertEqual(row["raceNumber"], 99)
        self.assertEqual(row["circuit"], "地方")

    def test_day_filters_other_dates(self):
        race = build_race()
        payload = day_payload("2026-10-29", [race])
        self.assertEqual(payload["races"], [])
        self.assertEqual(payload["raceCount"], 0)


class RacePayloadTests(unittest.TestCase):
    def setUp(self):
        self.race = build_race()
        self.payload = build_payload(self.race)
        self.detail = self.payload["detail"]
        self.unified = self.detail["unifiedForecast"]

    def test_envelope_shape(self):
        self.assertTrue(self.payload["ok"])
        self.assertEqual(self.payload["race_id"], self.race.race_id)
        self.assertIn("summary", self.payload)
        self.assertEqual(self.payload["summary"]["race_id"], self.race.race_id)
        self.assertTrue(self.payload["analysis_ready"])

    def test_detail_header_and_horses(self):
        for key in ("id", "circuit", "date", "track", "raceNumber",
                    "title", "distance", "surface", "weather", "condition",
                    "fieldSize", "startTime", "scheduledStartTime",
                    "horses", "result"):
            self.assertIn(key, self.detail)
        self.assertEqual(self.detail["fieldSize"], 5)
        horse0 = self.detail["horses"][0]
        for key in ("horseNumber", "frameNumber", "name", "age", "sex",
                    "carriedWeight", "jockey", "trainer", "status",
                    "scratched", "winOdds", "bodyWeight",
                    "bodyWeightChange", "recentRaces", "allPastRuns"):
            self.assertIn(key, horse0)
        run = horse0["recentRaces"][0]
        for key in ("date", "track", "distance", "finish", "fieldSize",
                    "cornerPositions"):
            self.assertIn(key, run)
        # Past runs must be strictly before the race date (UI re-checks).
        self.assertTrue(all(r["date"] < self.race.date
                            for r in horse0["allPastRuns"]))

    def test_truthful_flags(self):
        self.assertIs(self.unified["probabilitiesCalibrated"], False)
        self.assertIs(self.unified["researchOnly"], True)
        self.assertIs(self.unified["humanOverrides"], False)

    def test_unified_gate_fields(self):
        self.assertEqual(self.unified["version"], "arvexq-unified-live-v1")
        self.assertEqual(self.unified["raceId"], self.race.race_id)
        self.assertEqual(self.unified["raceDate"], self.race.date)
        self.assertEqual(self.unified["circuit"], self.detail["circuit"])
        self.assertEqual(len(self.unified["roster"]),
                         len(self.detail["horses"]))
        self.assertLess(self.unified["trainedThrough"], self.race.date)
        self.assertTrue(re.fullmatch(r"[a-f0-9]{64}",
                                     self.unified["receiptSha256"]))
        self.assertTrue(re.fullmatch(r"[a-f0-9]{64}",
                                     self.unified["modelHash"]))
        self.assertEqual(self.unified["modelHash"], model_hash(BETA))

    def test_marks_consistent_between_views(self):
        prediction = {m["horseNumber"]: m["mark"]
                      for m in self.detail["predictionMarks"]}
        unified = {m["horseNumber"]: m["markSymbol"]
                   for m in self.unified["marks"]}
        self.assertEqual(prediction, unified)
        self.assertEqual(sorted(prediction.values(),
                                  key=MARK_ORDER.index), MARK_ORDER)
        self.assertEqual(list(prediction.values()).count("◎"), 1)
        honmei = next(n for n, m in prediction.items() if m == "◎")
        self.assertEqual(self.unified["honmeiHorseNumber"], honmei)
        # No fabricated probability ranges; point estimates are present.
        for entry in self.unified["marks"]:
            self.assertIsNone(entry["winProbabilityRange"])
            self.assertIsNone(entry["top3ProbabilityRange"])
            self.assertIsNotNone(entry["winProbability"])
        for entry in self.detail["predictionMarks"]:
            self.assertIsNotNone(entry["winProbability"])

    def test_diagnosis_covers_all_runners(self):
        diagnosis = self.unified["diagnosis"]
        roster = {h["horseNumber"] for h in self.detail["horses"]}
        self.assertEqual({d["horseNumber"] for d in diagnosis}, roster)
        marks = {m["horseNumber"]: m for m in self.unified["marks"]}
        for entry in diagnosis:
            # The ability layer's raw score, never the win probability.
            self.assertIsNotNone(entry["abilityScore"])
            self.assertGreaterEqual(entry["abilityScore"], 0.0)
            self.assertLessEqual(entry["abilityScore"], 1.0)
            self.assertIsNotNone(entry["winProbability"])
            self.assertIsNotNone(entry["top3Probability"])
            self.assertTrue(entry["reason"])
            marked = marks.get(entry["horseNumber"])
            if marked is not None:
                self.assertEqual(entry["winProbability"],
                                 marked["winProbability"])
                self.assertEqual(entry["top3Probability"],
                                 marked["top3Probability"])

    def test_four_pace_stages(self):
        keys = [s["key"] for s in self.unified["paceStages"]]
        self.assertEqual(keys, ["start", "turn3", "turn4", "straight"])
        roster = {h["horseNumber"] for h in self.detail["horses"]}
        for stage in self.unified["paceStages"]:
            self.assertTrue(stage["pack"])
            for cell in stage["pack"]:
                self.assertIn(cell["no"], roster)
                self.assertGreaterEqual(cell["lane"], -2)
                self.assertLessEqual(cell["lane"], 2)

    def test_recommended_bets_match_tickets(self):
        race = self.race
        forecast = forecast_race(race, beta=BETA)
        odds = {r.number: r.win_odds.value
                for r in race.runners if r.win_odds.present}
        plan = generate_tickets(forecast, odds, calibration_validated=False)
        bets = self.detail["recommendedBets"]
        self.assertEqual(len(bets), len(plan.probability_tickets))
        by_combo = {(b["kind"], tuple(b["combos"][0])): b for b in bets}
        for ticket in plan.probability_tickets:
            label = {"win": "単勝", "place": "複勝", "wide": "ワイド",
                     "quinella": "馬連", "exacta": "馬単", "trio": "3連複",
                     "trifecta": "3連単"}[ticket.kind]
            bet = by_combo[(label, ticket.selection)]
            self.assertAlmostEqual(bet["probability"], ticket.probability)
            self.assertAlmostEqual(bet["comboProbabilities"][0],
                                   round(ticket.probability * 100, 1))
        # The UI ticket lane is a filtered subset of the same tickets.
        ui_kinds = {"馬連", "馬単", "ワイド", "3連複", "3連単"}
        items = self.unified["ticketPlan"]["items"]
        self.assertLessEqual(len(items), 5)
        self.assertTrue(all(i["kind"] in ui_kinds for i in items))
        self.assertIs(self.unified["ticketPlan"]["sameModelAndMarks"], True)

    def test_win_ev_shown_only_as_uncalibrated_estimate(self):
        # The purchase-candidate lanes still carry no EV numbers.
        for bet in self.detail["recommendedBets"]:
            self.assertIsNone(bet["expectedValue"])
            self.assertIsNone(bet["stakeUnits"])
        plan_block = self.unified["ticketPlan"]
        self.assertIsNone(plan_block["expectedValue"])
        self.assertEqual(
            plan_block["expectedValueStatus"], "uncalibrated-estimate")
        self.assertIn("未校正", plan_block["reason"])
        self.assertIn("推定値", plan_block["reason"])
        # Every fixture horse has real win odds (5.0): each estimate
        # must equal the model win probability x those odds.
        estimates = plan_block["winExpectedValues"]
        self.assertEqual(len(estimates), 5)
        for entry in estimates:
            self.assertAlmostEqual(entry["odds"], 5.0)
            self.assertAlmostEqual(
                entry["expectedValue"],
                entry["winProbability"] * entry["odds"],
                delta=1e-3,
            )
        # Combination items never carry an EV figure (no real odds).
        for item in plan_block["items"]:
            self.assertNotIn("expectedValue", item)

    def test_missing_provenance_fails_closed(self):
        payload = build_payload(self.race, provenance=None)
        unified = payload["detail"]["unifiedForecast"]
        self.assertIsNone(unified["receiptSha256"])
        self.assertIsNone(unified["capturedAt"])

    def test_insufficient_forecast_has_no_marks_or_bets(self):
        debut = normalize_race(
            dict(SUMMARY, title="2歳初出走"),
            {"horses": [horse(1, []), horse(2, []), horse(3, [])]},
            "test://x",
        )
        payload = build_payload(debut)
        detail = payload["detail"]
        self.assertEqual(detail["predictionMarks"], [])
        self.assertEqual(detail["recommendedBets"], [])
        self.assertEqual(detail["unifiedForecast"]["marks"], [])
        self.assertFalse(payload["analysis_ready"])


if __name__ == "__main__":
    unittest.main()
