"""pace-label-v2 realized labels (2026-11-26).

The v1 label (first-corner position ratios) was a mechanical
function of field size — every 9+ field labelled "fast" — and its
frequencies lost to plain climatology in walk-forward. v2 labels
by time instead: the median deceleration of the horses that
contested the early lead, condition-adjusted and standardized
against a frozen par table. These tests pin the definition's
load-bearing properties: field-size independence, the observation
gate, the condition adjustment, the par fallback, and the
label-version guard on frequency counting.
"""
import json
import tempfile
import unittest
from pathlib import Path

from rewrite.analysis.pace_scenario_freq import (
    LABEL_VERSION, front_deceleration, load_par_table,
    realized_pace_label, scenario_frequencies)

DISTANCE = 1400


def finisher(corner, b, last3f=40.0, distance=DISTANCE):
    """A finisher whose deceleration statistic equals ``b``."""
    t = last3f + (b + last3f) * (distance - 600) / 600.0
    return {"cornerPositions": [corner], "timeSeconds": round(t, 3),
            "last3FSeconds": last3f}


def par(entries=None, shift_keys=None, shift_surfaces=None):
    return {
        "entries": entries if entries is not None
        else {("ダート", DISTANCE): (0.0, 1.0)},
        "shift_keys": shift_keys or {},
        "shift_surfaces": shift_surfaces or {},
    }


class FrontDecelerationTests(unittest.TestCase):
    def test_median_over_early_leaders_only(self):
        finishers = [finisher(1, -2.0), finisher(2, -1.0),
                     finisher(3, -3.0),
                     finisher(8, 5.0), finisher(9, 6.0)]
        # The two deep closers must not move the statistic.
        self.assertAlmostEqual(
            front_deceleration(finishers, DISTANCE), -2.0, places=2)

    def test_gate_needs_two_observed_leaders(self):
        self.assertIsNone(front_deceleration([finisher(1, -2.0)],
                                             DISTANCE))
        missing_times = [{"cornerPositions": [1]},
                         {"cornerPositions": [2]}]
        self.assertIsNone(front_deceleration(missing_times, DISTANCE))

    def test_field_size_cannot_change_the_statistic(self):
        leaders = [finisher(1, -1.5), finisher(2, -1.0),
                   finisher(3, -2.0)]
        small = front_deceleration(leaders, DISTANCE)
        big_field = leaders + [finisher(c, 3.0) for c in range(4, 17)]
        self.assertEqual(front_deceleration(big_field, DISTANCE), small)


class RealizedLabelTests(unittest.TestCase):
    def label(self, finishers, **kwargs):
        kwargs.setdefault("surface", "ダート")
        kwargs.setdefault("distance", DISTANCE)
        kwargs.setdefault("condition", "良")
        kwargs.setdefault("par", par())
        return realized_pace_label(finishers, **kwargs)

    def test_thresholds(self):
        fast = [finisher(1, -1.0), finisher(2, -1.0)]
        slow = [finisher(1, 1.0), finisher(2, 1.0)]
        normal = [finisher(1, 0.0), finisher(2, 0.0)]
        self.assertEqual(self.label(fast)["label"], "fast")
        self.assertEqual(self.label(slow)["label"], "slow")
        self.assertEqual(self.label(normal)["label"], "normal")

    def test_wet_condition_shift_prevents_spurious_fast(self):
        # Raw B = -0.9 would be "fast" on a good track; on a wet
        # track the frozen shift (-0.5) explains most of it, so the
        # adjusted z is only -0.4 -> normal.
        leaders = [finisher(1, -0.9), finisher(2, -0.9)]
        wet_par = par(shift_keys={("ダート", DISTANCE): -0.5})
        wet = self.label(leaders, condition="稍重", par=wet_par)
        dry = self.label(leaders, condition="良", par=wet_par)
        self.assertEqual(wet["label"], "normal")
        self.assertEqual(dry["label"], "fast")

    def test_par_falls_back_to_nearest_distance(self):
        leaders = [finisher(1, -1.0), finisher(2, -1.0)]
        only_1500 = par(entries={("ダート", 1500): (0.0, 1.0)})
        out = self.label(leaders, par=only_1500)
        self.assertEqual(out["label"], "fast")

    def test_no_par_for_surface_is_unlabelled(self):
        leaders = [finisher(1, -1.0), finisher(2, -1.0)]
        self.assertIsNone(self.label(leaders, surface="芝"))


class ParTableTests(unittest.TestCase):
    def test_roundtrip_and_missing_file(self):
        doc = {
            "par": {"ダート|1400": {"median": -1.5, "spread": 1.2,
                                    "n": 100}},
            "conditionShifts": {
                "keys": {"ダート|1400": -0.3},
                "surfaces": {"ダート": -0.28}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "par.json"
            path.write_text(json.dumps(doc, ensure_ascii=False),
                            encoding="utf-8")
            table = load_par_table(path)
            missing = load_par_table(Path(tmp) / "nope.json")
        self.assertEqual(table["entries"][("ダート", 1400)], (-1.5, 1.2))
        self.assertEqual(table["shift_keys"][("ダート", 1400)], -0.3)
        self.assertEqual(table["shift_surfaces"]["ダート"], -0.28)
        self.assertEqual(missing["entries"], {})


class VersionGuardTests(unittest.TestCase):
    def test_other_version_rows_are_not_counted(self):
        rows = ([{"date": "2026-11-20", "track": "名古屋",
                  "surface": "ダート", "distance": 1500,
                  "label": "fast",
                  "labelVersion": LABEL_VERSION}] * 20
                + [{"date": "2026-11-20", "track": "名古屋",
                    "surface": "ダート", "distance": 1500,
                    "label": "slow",
                    "labelVersion": "pace-label-v1"}] * 20)
        freq = scenario_frequencies(rows, track="名古屋",
                                    surface="ダート", distance=1500)
        self.assertEqual(freq["sample"], 20)
        self.assertEqual(freq["fast"], 1.0)
        self.assertEqual(freq["labelVersion"], LABEL_VERSION)


if __name__ == "__main__":
    unittest.main()
