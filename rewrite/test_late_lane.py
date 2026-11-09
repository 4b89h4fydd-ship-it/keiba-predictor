"""Tests for the yukochi-style late lane (S2 shadow).

Covers the pure late-input transforms and the Phase 0 gate:
applying late facts must change exactly the field the late facts
describe (scratches leave the active field, jockey/going override,
body weight attaches with late provenance), absent facts change
nothing, and the gate stays closed unless every audited value is
literally true.
"""
import json
import tempfile
import unittest
from pathlib import Path

from rewrite.analysis.late_lane import (
    LateInputs,
    apply_late_inputs,
    gate_open,
    late_inputs_from_api_payload,
    late_inputs_from_snapshot,
)
from rewrite.data.normalize import normalize_race


def run(date, corners, finish, behind=0.5):
    return {
        "date": date, "track": "大井", "distance": 1600, "surface": "ダート",
        "finish": finish, "fieldSize": 10, "cornerPositions": corners,
        "marginText": "", "timeSeconds": 98.0, "jockey": "騎手",
        "condition": "良", "weather": "晴", "timeBehindWinner": behind,
        "marginSeconds": behind, "carriedWeight": 56.0,
    }


def horse(number, runs, **overrides):
    base = {
        "horseNumber": number, "id": f"h{number}", "name": f"馬{number}",
        "frameNumber": number, "age": 4, "sex": "牡", "jockey": "騎手A",
        "trainer": "調教師", "carriedWeight": 56.0, "bodyWeight": None,
        "bodyWeightChange": None, "winOdds": None, "scratched": False,
        "allPastRuns": runs,
    }
    base.update(overrides)
    return base


SUMMARY = {
    "race_id": "nar-2026-10-29-大井-01", "race_date": "2026-10-29",
    "circuit": "地方", "track": "大井", "race_no": 1,
    "start_time": "14:30", "title": "テスト", "surface": "ダート",
    "distance": 1600, "weather": "晴", "condition": "良", "updated_at": 1,
}

RUNS = [run("2026-10-01", [1, 1, 1, 1], 2), run("2026-09-01", [2, 1, 1, 1], 3)]


def make_race():
    return normalize_race(
        SUMMARY,
        {"horses": [horse(1, RUNS), horse(2, RUNS), horse(3, RUNS)]},
        "test://x")


class ApplyLateInputsTests(unittest.TestCase):
    def test_scratch_removes_runner_from_active_field(self):
        race = apply_late_inputs(make_race(), LateInputs(scratched={2: True}))
        self.assertEqual([r.number for r in race.active_runners], [1, 3])
        self.assertEqual(len(race.runners), 3)

    def test_jockey_and_condition_override_with_late_provenance(self):
        race = apply_late_inputs(
            make_race(),
            LateInputs(condition="重", weather="雨", jockey={1: "騎手B"}))
        self.assertEqual(race.condition.value, "重")
        self.assertEqual(race.weather.value, "雨")
        by_no = {r.number: r for r in race.runners}
        self.assertEqual(by_no[1].jockey.value, "騎手B")
        self.assertEqual(by_no[1].jockey.source, "late-api-t30")
        self.assertEqual(by_no[2].jockey.value, "騎手A")

    def test_body_weight_attaches_and_coverage_counts(self):
        late = LateInputs(body_weight={1: 512.0, 3: 498.0},
                          body_weight_change={1: 4.0})
        race = apply_late_inputs(make_race(), late)
        by_no = {r.number: r for r in race.runners}
        self.assertEqual(by_no[1].body_weight.value, 512.0)
        self.assertEqual(by_no[1].body_weight_change.value, 4.0)
        self.assertFalse(by_no[2].body_weight.present)
        self.assertAlmostEqual(late.body_weight_coverage([1, 2, 3]), 2 / 3)

    def test_absent_facts_change_nothing(self):
        race = make_race()
        same = apply_late_inputs(race, LateInputs())
        self.assertEqual(same, race)


class FromPayloadTests(unittest.TestCase):
    def test_api_payload_routing(self):
        payload = {
            "summary": {"condition": "重", "weather": "雨"},
            "detail": {"horses": [
                {"horseNumber": 1, "jockey": "騎手B", "scratched": True,
                 "bodyWeight": 512, "bodyWeightChange": 4, "winOdds": 3.2,
                 "popularity": 1},
                {"horseNumber": 2, "jockey": "騎手A"},
            ]},
            "odds": [
                {"horse_no": 2, "body_weight": 480,
                 "body_weight_change": -2, "win_odds": 9.5,
                 "popularity": 3},
            ],
        }
        late = late_inputs_from_api_payload(payload)
        self.assertEqual(late.condition, "重")
        self.assertEqual(late.scratched, {1: True})
        self.assertEqual(late.body_weight, {1: 512.0, 2: 480.0})
        self.assertEqual(late.body_weight_change, {1: 4.0, 2: -2.0})
        self.assertEqual(late.win_odds, {1: 3.2, 2: 9.5})

    def test_unknown_summary_condition_stays_missing(self):
        late = late_inputs_from_api_payload(
            {"summary": {"condition": "不明"}, "detail": {"horses": []}})
        self.assertIsNone(late.condition)

    def test_snapshot_round_trip(self):
        snapshot = [{"no": 1, "jockey": "騎手B", "scratched": False,
                     "bodyWeight": 512, "bodyWeightChange": 4,
                     "winOdds": 3.2, "popularity": 1},
                    {"no": 2, "jockey": "騎手A", "scratched": True,
                     "bodyWeight": None, "bodyWeightChange": None,
                     "winOdds": None, "popularity": None}]
        late = late_inputs_from_snapshot(snapshot, condition="重")
        self.assertEqual(late.body_weight, {1: 512.0})
        self.assertEqual(late.scratched, {2: True})
        self.assertEqual(late.condition, "重")


class GateTests(unittest.TestCase):
    def _summary(self, gate):
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"gates": gate}, tmp)
        tmp.close()
        return Path(tmp.name)

    def test_gate_opens_only_when_all_true(self):
        path = self._summary({"a": True, "b": True})
        self.assertTrue(gate_open(path)[0])
        path = self._summary({"a": True, "b": None})
        self.assertFalse(gate_open(path)[0])
        path = self._summary({"a": False})
        self.assertFalse(gate_open(path)[0])

    def test_missing_summary_keeps_gate_closed(self):
        self.assertFalse(gate_open(Path("/nonexistent/summary.json"))[0])


if __name__ == "__main__":
    unittest.main()
