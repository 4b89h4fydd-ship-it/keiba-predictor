# -*- coding: utf-8 -*-
"""weight_repair_targets / preserve_present_weights tests
(2026-11-09, direct-acquisition plan §7.2).

The official NAR card publishes every runner's current body weight
only ~60 minutes before post. The chain that carries it into a
stored detail (odds_refresh's official card fallback -> merge_live
-> the durable-write gate) works when invoked, but invocation was
left to ordinary targeting and a scheduler-starved sync workflow
(11 completed runs on 2026-11-09), so most races never saw a run
inside their publication window and kept the pre-publication card
forever (entry-side coverage 51.8%, all-or-nothing per race).
A stored NAR race whose card entries still lack a weight must be
an explicit sync target on every run inside the window, and the
repair may only fill missing values — never rewrite a stored one.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "arvexq_live_sync", ROOT / "scripts" / "arvexq_live_sync.py")
live_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_sync)

weight_repair_targets = live_sync.weight_repair_targets
preserve_present_weights = live_sync.preserve_present_weights


def row(rid, start, track="佐賀", circuit="地方"):
    h, m = divmod(start, 60)
    return {"id": rid, "track": track, "circuit": circuit,
            "startTime": f"{h:02d}:{m:02d}"}


def horse(no, weight="present", scratched=False, status=""):
    h = {"horseNumber": no, "scratched": scratched, "status": status}
    if weight == "present":
        h["bodyWeight"] = 480
        h["bodyWeightChange"] = 2
    elif weight == "missing":
        h["bodyWeight"] = None
        h["bodyWeightChange"] = None
    return h


def detail(horses):
    return {"horses": horses}


class WeightRepairTargetsTest(unittest.TestCase):
    NOW = 15 * 60 + 30  # 15:30; Saga 4R posts 16:20 (50 min out)

    def test_incomplete_race_in_window_is_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2, "missing"), horse(3)])}
        self.assertEqual(
            weight_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_complete_race_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-05", 16 * 60 + 55)]
        details = {"nar-2026-11-09-佐賀-05": detail([horse(1), horse(2)])}
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_only_scratched_missing_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-06", 16 * 60 + 40)]
        details = {"nar-2026-11-09-佐賀-06": detail(
            [horse(1), horse(2, "missing", scratched=True, status="出走取消")])}
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_jra_race_is_not_targeted(self):
        rows = [row("jra-2026-11-09-東京-11", 16 * 60 + 20,
                    track="東京", circuit="中央")]
        details = {"jra-2026-11-09-東京-11": detail([horse(1, "missing")])}
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_before_window_is_not_targeted(self):
        # 120 minutes out: the official card has published nothing
        # yet; the race joins the repair set when the window opens.
        rows = [row("nar-2026-11-09-佐賀-08", 18 * 60 + 30)]
        details = {"nar-2026-11-09-佐賀-08": detail([horse(1, "missing")])}
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_inside_min_lead_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-03", self.NOW + 3)]
        details = {"nar-2026-11-09-佐賀-03": detail([horse(1, "missing")])}
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_already_started_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-02", self.NOW - 20)]
        details = {"nar-2026-11-09-佐賀-02": detail([horse(1, "missing")])}
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_unreadable_detail_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20),
                row("nar-2026-11-09-佐賀-05", 16 * 60 + 40),
                row("nar-2026-11-09-佐賀-06", 16 * 60 + 55)]
        details = {
            "nar-2026-11-09-佐賀-04": {},
            "nar-2026-11-09-佐賀-05": {"horses": []},
            # nar-2026-11-09-佐賀-06: no detail at all.
        }
        self.assertEqual(weight_repair_targets(rows, details, self.NOW), [])

    def test_zero_weight_counts_as_missing(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        h = horse(1)
        h["bodyWeight"] = 0
        details = {"nar-2026-11-09-佐賀-04": detail([h])}
        self.assertEqual(
            weight_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_nearest_post_first(self):
        rows = [row("nar-2026-11-09-佐賀-05", 16 * 60 + 40),
                row("nar-2026-11-09-佐賀-04", 16 * 60 + 20),
                row("nar-2026-11-09-佐賀-06", 16 * 60 + 5)]
        details = {r["id"]: detail([horse(1, "missing")]) for r in rows}
        self.assertEqual(
            weight_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-06", "nar-2026-11-09-佐賀-04",
             "nar-2026-11-09-佐賀-05"])


class PreservePresentWeightsTest(unittest.TestCase):
    def test_stored_weight_survives_a_different_refreshed_value(self):
        base = {"horses": [{"horseNumber": 1, "bodyWeight": 480,
                            "bodyWeightChange": 2}]}
        merged = {"horses": [{"horseNumber": 1, "bodyWeight": 484,
                              "bodyWeightChange": 6}]}
        out = preserve_present_weights(base, merged)
        self.assertEqual(out["horses"][0]["bodyWeight"], 480)
        self.assertEqual(out["horses"][0]["bodyWeightChange"], 2)

    def test_missing_weight_takes_the_refreshed_value(self):
        base = {"horses": [{"horseNumber": 1, "bodyWeight": None,
                            "bodyWeightChange": None}]}
        merged = {"horses": [{"horseNumber": 1, "bodyWeight": 465,
                              "bodyWeightChange": 1}]}
        out = preserve_present_weights(base, merged)
        self.assertEqual(out["horses"][0]["bodyWeight"], 465)
        self.assertEqual(out["horses"][0]["bodyWeightChange"], 1)

    def test_horse_absent_from_base_is_untouched(self):
        base = {"horses": [{"horseNumber": 1, "bodyWeight": 480,
                            "bodyWeightChange": 2}]}
        merged = {"horses": [{"horseNumber": 2, "bodyWeight": 500,
                              "bodyWeightChange": 0}]}
        out = preserve_present_weights(base, merged)
        self.assertEqual(out["horses"][0]["bodyWeight"], 500)

    def test_unreadable_inputs_pass_through(self):
        merged = {"horses": []}
        self.assertIs(preserve_present_weights(None, merged), merged)
        self.assertIsNone(preserve_present_weights({"horses": []}, None))


if __name__ == "__main__":
    unittest.main()
