"""Scenario-probability wiring (2026-11-26, user directive).

The pace text must show a measured probability and its consequence
("確率だして、これやからこうなる"). The probabilities are the
empirical frequencies of realized historical labels measured by
``pace_scenario_freq`` — with sample size and scope attached — and
races without enough measured history keep null probabilities and
the previous label-only text. Nothing here is an accuracy claim
about the frequencies themselves; the forward-validation
registration (candidate C) grades them separately.
"""
import json
import tempfile
import unittest
from pathlib import Path

from rewrite.analysis.forecast import forecast_race
from rewrite.analysis.pace import forecast_pace
from rewrite.analysis.pace_scenario_freq import (
    load_scenario_history, scenario_frequency_for, scenario_frequencies)
from rewrite.analysis.tickets import generate_tickets
from rewrite.data.normalize import normalize_race
from rewrite.output.api_shape import race_payload
from rewrite.test_analysis import (
    CLOSER_RUNS, FRONT_RUNS, MID_RUNS, SUMMARY, horse)

BETA = 2.0
PROVENANCE = {"snapshot_sha256": "a" * 64,
              "captured_at": "2026-10-28T01:00:00+09:00", "odds": []}
FREQUENCY = {"slow": 0.10, "normal": 0.25, "fast": 0.65,
             "sample": 40, "scope": "track-surface",
             "labelVersion": "pace-label-v2"}


def build_payload(horses, **kwargs):
    race = normalize_race(SUMMARY, {"horses": horses}, "test://x")
    forecast = forecast_race(race, beta=BETA)
    pace = forecast_pace(race)
    odds = {r.number: r.win_odds.value
            for r in race.runners if r.win_odds.present}
    tickets = generate_tickets(forecast, odds, calibration_validated=False)
    return race_payload(race, forecast, pace, tickets,
                        provenance=PROVENANCE, **kwargs)


def history_rows(n_fast, n_normal, n_slow, *, date="2026-11-20",
                 track="名古屋", surface="ダート", distance=1500):
    rows = []
    for label, count in (("fast", n_fast), ("normal", n_normal),
                         ("slow", n_slow)):
        rows += [{"date": date, "track": track, "surface": surface,
                  "distance": distance, "label": label}] * count
    return rows


class FrequencyMeasurementTests(unittest.TestCase):
    def test_scopes_widen_and_sample_is_reported(self):
        rows = history_rows(13, 5, 2)  # exactly the 20-race floor
        freq = scenario_frequencies(rows, track="名古屋",
                                    surface="ダート", distance=1500)
        self.assertEqual(freq["sample"], 20)
        self.assertEqual(freq["scope"], "track-surface-distance")
        self.assertAlmostEqual(
            freq["slow"] + freq["normal"] + freq["fast"], 1.0)

    def test_below_floor_at_every_scope_is_unmeasured(self):
        rows = history_rows(10, 5, 2)
        self.assertIsNone(scenario_frequencies(
            rows, track="名古屋", surface="ダート", distance=1500))

    def test_before_date_cut_is_walk_forward(self):
        rows = (history_rows(20, 0, 0, date="2026-11-20")
                + history_rows(0, 0, 25, date="2026-11-26"))
        freq = scenario_frequency_for(
            rows, track="名古屋", surface="ダート", distance=1500,
            before_date="2026-11-26")
        # The 25 slow rows are dated ON the target date and must
        # not leak in: only the 20 earlier fast rows count.
        self.assertEqual(freq["sample"], 20)
        self.assertEqual(freq["fast"], 1.0)

    def test_loader_tolerates_missing_and_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.jsonl"
            self.assertEqual(load_scenario_history(missing), [])
            path = Path(tmp) / "history.jsonl"
            path.write_text(
                json.dumps({"date": "2026-11-20", "label": "fast"}) + "\n"
                "not json\n\n", encoding="utf-8")
            rows = load_scenario_history(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["label"], "fast")


class PaceBlockWiringTests(unittest.TestCase):
    def test_unmeasured_race_keeps_null_and_old_text(self):
        payload = build_payload([
            horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
            horse(3, MID_RUNS), horse(4, CLOSER_RUNS),
            horse(5, MID_RUNS)])
        pace = payload["detail"]["unifiedForecast"]["pace"]
        self.assertIsNone(pace["scenarioProbabilities"])
        self.assertFalse(pace["scenarioFrequencyMeasured"])
        self.assertNotIn("実績では、ペースは",
                         payload["detail"]["forecastText"])

    def test_measured_race_publishes_probability_and_consequence(self):
        payload = build_payload(
            [horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
             horse(3, MID_RUNS), horse(4, CLOSER_RUNS),
             horse(5, MID_RUNS)],
            scenario_frequency=FREQUENCY)
        pace = payload["detail"]["unifiedForecast"]["pace"]
        self.assertEqual(pace["scenarioProbabilities"],
                         {"slow": 0.10, "normal": 0.25, "fast": 0.65})
        self.assertTrue(pace["scenarioFrequencyMeasured"])
        self.assertEqual(pace["scenarioFrequencySample"], 40)
        self.assertEqual(pace["scenarioLabelVersion"], "pace-label-v2")
        text = payload["detail"]["forecastText"]
        # The pace block and the forecast text are the same block.
        self.assertEqual(text, pace["text"])
        self.assertIn("ハイ65%・ミドル25%・スロー10%", text)
        self.assertIn("過去40レースの実績", text)
        self.assertIn("名古屋ダート", text)  # track-surface scope
        # Consequence follows the most frequent scenario (fast).
        self.assertIn("先行勢は競り合って苦しくなり", text)

    def test_consequence_follows_the_argmax_scenario(self):
        slow_first = {"slow": 0.60, "normal": 0.30, "fast": 0.10,
                      "sample": 30, "scope": "surface"}
        payload = build_payload(
            [horse(1, FRONT_RUNS), horse(2, CLOSER_RUNS),
             horse(3, MID_RUNS), horse(4, CLOSER_RUNS),
             horse(5, MID_RUNS)],
            scenario_frequency=slow_first)
        text = payload["detail"]["forecastText"]
        self.assertIn("ハイ10%・ミドル30%・スロー60%", text)
        self.assertIn("前が残りやすく", text)

    def test_display_percentages_sum_to_100(self):
        from rewrite.output.api_shape import _scenario_percentages
        freq = {"slow": 0.333, "normal": 0.333, "fast": 0.334}
        pct = _scenario_percentages(freq)
        self.assertEqual(sum(pct.values()), 100)


if __name__ == "__main__":
    unittest.main()
