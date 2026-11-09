# -*- coding: utf-8 -*-
"""choose_targets coverage-earliness tests.

The realtime sync is the only lane that lands official place odds
into stored details, and the publish lane's place-EV upgrade guard
closes at post-60min while official odds stand only ~60-100 min
before post. Target selection therefore has to cover races hours
ahead of post (a single landed run inside the stand-up window must
suffice), nearest posts first, capped so a run stays inside its
job timeout. Venue live/next picks are the pre-existing behaviour
and must be preserved.
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

choose_targets = live_sync.choose_targets


def row(rid, track, start, circuit="地方"):
    h, m = divmod(start, 60)
    return {"id": rid, "track": track, "circuit": circuit,
            "startTime": f"{h:02d}:{m:02d}"}


class ChooseTargetsTest(unittest.TestCase):
    NOW = 12 * 60 + 0  # 12:00

    def test_venue_live_and_next_future_picks_preserved(self):
        rows = [
            row("a-live", "園田", self.NOW - 10),
            row("a-next", "園田", self.NOW + 30),
            row("a-far", "園田", self.NOW + 600),
            row("b-next", "金沢", self.NOW + 45),
        ]
        ids = choose_targets(rows, self.NOW)
        self.assertIn("a-live", ids)
        self.assertIn("a-next", ids)
        self.assertIn("b-next", ids)
        # The venue's far-future race is only a first pick when it is
        # the next one; here it is neither next nor inside the sweep.
        self.assertNotIn("a-far", ids)

    def test_sweep_covers_races_hours_ahead(self):
        rows = [
            row("v-next", "園田", self.NOW + 20),
            row("v-plus180", "園田", self.NOW + 180),
            row("v-plus239", "園田", self.NOW + 239),
        ]
        ids = choose_targets(rows, self.NOW)
        self.assertIn("v-plus180", ids)
        self.assertIn("v-plus239", ids)

    def test_sweep_excludes_beyond_four_hours(self):
        rows = [
            row("v-next", "園田", self.NOW + 20),
            row("v-plus241", "園田", self.NOW + 241),
            row("v-plus300", "園田", self.NOW + 300),
        ]
        ids = choose_targets(rows, self.NOW)
        self.assertNotIn("v-plus241", ids)
        self.assertNotIn("v-plus300", ids)

    def test_recently_started_race_stays_in_sweep(self):
        rows = [
            row("v-next", "園田", self.NOW + 20),
            row("v-just-started", "金沢", self.NOW - 14),
            row("v-long-gone", "金沢", self.NOW - 40),
        ]
        ids = choose_targets(rows, self.NOW)
        self.assertIn("v-just-started", ids)
        self.assertNotIn("v-long-gone", ids)

    def test_cap_keeps_nearest_posts(self):
        rows = [row("v-next", "園田", self.NOW + 5)]
        for i in range(40):
            rows.append(row(f"r{i:02d}", "金沢", self.NOW + 30 + i * 5))
        ids = choose_targets(rows, self.NOW)
        self.assertLessEqual(len(ids), live_sync.MAX_LIVE_TARGETS)
        # The nearest sweep races are in; the farthest are the ones cut.
        self.assertIn("r00", ids)
        self.assertNotIn("r39", ids)
        kept_offsets = sorted(
            int(r["startTime"][:2]) * 60 + int(r["startTime"][3:])
            for r in rows if r["id"] in ids and r["id"].startswith("r"))
        dropped = [r for r in rows
                   if r["id"].startswith("r") and r["id"] not in ids]
        for r in dropped:
            off = int(r["startTime"][:2]) * 60 + int(r["startTime"][3:])
            self.assertGreater(off, max(kept_offsets))

    def test_no_duplicates(self):
        rows = [
            row("v-live", "園田", self.NOW - 5),
            row("v-next", "園田", self.NOW + 30),
            row("v-mid", "園田", self.NOW + 90),
        ]
        ids = choose_targets(rows, self.NOW)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
