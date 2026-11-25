"""Honesty regressions for the pace block and calibration labelling.

Covers two defects measured on the 2026-11-25 production packs:

- Nagoya 12R had observedPositionCoverage 12/12 and unknown=[], yet
  forecastText claimed "過去走の初角位置の観測不足" because the text
  fired whenever the front-runner list was empty, regardless of how
  much was actually observed.
- The same race's mark reason said （校正済み） while the payload's
  probabilitiesCalibrated flag was false: the publisher passed
  ``calibrated_probabilities=used_v9b`` into race_payload, flipping
  every human-facing text while the machine flag stayed false.

Upload-ready adaptation (2026-11-26): this file ships with the two
wording fixes only. The first-corner passthrough tests from the
original draft are omitted because main wires the verified value
post-build in the publisher (covered by
tests/test_course_geometry_wiring.py), and the scenario-frequency
tests are omitted because rewrite/analysis/pace_scenario_freq.py is
a forward-validation candidate that is not shipped here.
"""
import unittest

from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.pace import forecast_pace
from rewrite.analysis.tickets import generate_tickets
from rewrite.data.normalize import normalize_race
from rewrite.output.api_shape import (
    PROBABILITIES_CALIBRATED, _mark_reason, race_payload)
from rewrite.test_analysis import (
    CLOSER_RUNS, FRONT_RUNS, MID_RUNS, SUMMARY, horse)

BETA = 2.0
PROVENANCE = {"snapshot_sha256": "a" * 64,
              "captured_at": "2026-10-28T01:00:00+09:00", "odds": []}


def build_payload(horses, **kwargs):
    race = normalize_race(SUMMARY, {"horses": horses}, "test://x")
    forecast = forecast_race(race, beta=BETA)
    pace = forecast_pace(race)
    odds = {r.number: r.win_odds.value
            for r in race.runners if r.win_odds.present}
    tickets = generate_tickets(forecast, odds, calibration_validated=False)
    payload = race_payload(race, forecast, pace, tickets,
                           provenance=PROVENANCE, **kwargs)
    return payload


class PaceTextTests(unittest.TestCase):
    def test_no_front_but_all_observed_does_not_claim_shortage(self):
        payload = build_payload([
            horse(1, CLOSER_RUNS), horse(2, MID_RUNS),
            horse(3, CLOSER_RUNS), horse(4, MID_RUNS),
            horse(5, CLOSER_RUNS)])
        pace = payload["detail"]["unifiedForecast"]["pace"]
        self.assertEqual(pace["likelyForwardNumbers"], [])
        self.assertEqual(pace["unknownNumbers"], [])
        self.assertNotIn("観測不足", payload["detail"]["forecastText"])
        self.assertIn("先行型と判定された馬はなし",
                      payload["detail"]["forecastText"])
        self.assertIn("観測済み5頭", payload["detail"]["forecastText"])

    def test_unknown_runners_keep_shortage_text(self):
        payload = build_payload([
            horse(1, []), horse(2, CLOSER_RUNS), horse(3, MID_RUNS),
            horse(4, CLOSER_RUNS), horse(5, MID_RUNS)])
        pace = payload["detail"]["unifiedForecast"]["pace"]
        self.assertEqual(pace["likelyForwardNumbers"], [])
        self.assertNotEqual(pace["unknownNumbers"], [])
        self.assertIn("観測不足につき先行候補は未確認",
                      payload["detail"]["forecastText"])

    def test_front_runners_keep_candidate_text(self):
        payload = build_payload([
            horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
            horse(3, MID_RUNS), horse(4, CLOSER_RUNS),
            horse(5, MID_RUNS)])
        self.assertIn("前に行く候補は", payload["detail"]["forecastText"])


class CalibrationLabelTests(unittest.TestCase):
    def test_flag_and_texts_agree_when_publisher_uses_the_constant(self):
        # The publisher now passes PROBABILITIES_CALIBRATED itself, so
        # the human-facing texts can never contradict the flag again.
        payload = build_payload(
            [horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
             horse(3, MID_RUNS), horse(4, FRONT_RUNS), horse(5, MID_RUNS)],
            calibrated_probabilities=PROBABILITIES_CALIBRATED)
        unified = payload["detail"]["unifiedForecast"]
        self.assertFalse(unified["probabilitiesCalibrated"])
        self.assertFalse(PROBABILITIES_CALIBRATED)
        for mark in unified["marks"]:
            self.assertNotIn("（校正済み）", mark["reason"])
            if "勝率推定" in mark["reason"]:
                self.assertIn("（未校正）", mark["reason"])
        for row in unified["diagnosis"]:
            self.assertNotIn("（校正済み）", row["reason"])
        self.assertNotIn("校正済み", unified["ticketPlan"]["reason"])
        self.assertEqual(
            unified["analysisStages"]["probability"]["calibrated"],
            unified["probabilitiesCalibrated"])

    def test_mark_reason_switch_is_explicit(self):
        # Documents the two wordings the switch produces; production
        # must stay on the uncalibrated wording until a calibration
        # validation passes (see PROBABILITIES_CALIBRATED).

        class _R:
            p_win, p_top3, pace_reasons, status = 0.071, 0.230, (), "ok"
        self.assertIn("（未校正）", _mark_reason(_R(), calibrated=False))
        self.assertIn("（校正済み）", _mark_reason(_R(), calibrated=True))


if __name__ == "__main__":
    unittest.main()
