# -*- coding: utf-8 -*-
"""odds_repair_targets / RaceDataBank odds provenance tests
(2026-11-09, direct-acquisition plan §7.1).

The official OddsTanFuku fetch/parse leg is exact, but a stored
detail's win odds only change when a non-market field forces a
full write: the durable-write gate strips every market field
before fingerprinting, so an odds-only refresh lands in the
odds_current side table and never in the detail's horses. A
detail first written in the morning keeps the day's first,
tiny-pool official capture (Morioka 4R 2026-11-09: 26.0 for four
horses, 52.0 for four more, frozen hours before post) under a
"NAR公式" label. A stored NAR race whose win odds are missing,
not official-sourced, or stale must be an explicit sync target
whose refreshed detail is written in full.

The RaceDataBank half pins the per-horse provenance rule: the
odds store must keep each row's own oddsSource instead of
flattening every row to the caller's blanket label, because
_restore_saved_odds rebuilds detail horses from those rows and
a flattened label re-stamps fallback values as official.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "arvexq_live_sync", ROOT / "scripts" / "arvexq_live_sync.py")
live_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live_sync)

odds_repair_targets = live_sync.odds_repair_targets


def row(rid, start, track="佐賀", circuit="地方"):
    h, m = divmod(start, 60)
    return {"id": rid, "track": track, "circuit": circuit,
            "startTime": f"{h:02d}:{m:02d}"}


def horse(no, odds=26.0, source="NAR公式", scratched=False, status=""):
    h = {"horseNumber": no, "scratched": scratched, "status": status}
    if odds is not None:
        h["winOdds"] = odds
    if source is not None:
        h["oddsSource"] = source
    return h


def detail(horses, stamp="15:20:00"):
    d = {"horses": horses}
    if stamp is not None:
        d["oddsUpdatedAt"] = stamp
    return d


class OddsRepairTargetsTest(unittest.TestCase):
    NOW = 15 * 60 + 30  # 15:30; Saga 4R posts 16:20 (50 min out)

    def test_stale_official_odds_are_targeted(self):
        # All official-sourced, but the stamp is from 10:22 — the
        # Morioka shape: a morning tiny-pool capture left standing.
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2)], stamp="10:22:30")}
        self.assertEqual(
            odds_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_fresh_official_odds_are_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2)], stamp="15:20:00")}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_missing_stamp_is_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2)], stamp=None)}
        self.assertEqual(
            odds_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_iso_stamp_is_understood(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        fresh = detail([horse(1)], stamp="2026-11-09T15:20:00+09:00")
        stale = detail([horse(1)], stamp="2026-11-09T09:00:00+09:00")
        self.assertEqual(
            odds_repair_targets(rows, {"nar-2026-11-09-佐賀-04": fresh},
                                self.NOW), [])
        self.assertEqual(
            odds_repair_targets(rows, {"nar-2026-11-09-佐賀-04": stale},
                                self.NOW), ["nar-2026-11-09-佐賀-04"])

    def test_missing_win_odds_are_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2, odds=None)])}
        self.assertEqual(
            odds_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_fallback_sourced_odds_are_targeted(self):
        # Fresh stamp, full field — but one horse's price came from
        # netkeiba, so the field must not stand as purely official.
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2, source="netkeiba実オッズ")])}
        self.assertEqual(
            odds_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_horse_without_any_source_is_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2, source=None)])}
        self.assertEqual(
            odds_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-04"])

    def test_only_scratched_missing_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20)]
        details = {"nar-2026-11-09-佐賀-04": detail(
            [horse(1), horse(2, odds=None, scratched=True,
                   status="出走取消")])}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_jra_race_is_not_targeted(self):
        rows = [row("jra-2026-11-09-東京-11", 16 * 60 + 20,
                    track="東京", circuit="中央")]
        details = {"jra-2026-11-09-東京-11": detail([horse(1, odds=None)])}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_beyond_max_lead_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-08", 21 * 60 + 0)]
        details = {"nar-2026-11-09-佐賀-08": detail([horse(1, odds=None)])}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_inside_min_lead_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-03", self.NOW + 5)]
        details = {"nar-2026-11-09-佐賀-03": detail([horse(1, odds=None)])}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_already_started_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-02", self.NOW - 20)]
        details = {"nar-2026-11-09-佐賀-02": detail([horse(1, odds=None)])}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_unreadable_detail_is_not_targeted(self):
        rows = [row("nar-2026-11-09-佐賀-04", 16 * 60 + 20),
                row("nar-2026-11-09-佐賀-05", 16 * 60 + 40)]
        details = {"nar-2026-11-09-佐賀-04": {}}
        self.assertEqual(odds_repair_targets(rows, details, self.NOW), [])

    def test_nearest_post_first(self):
        rows = [row("nar-2026-11-09-佐賀-05", 16 * 60 + 40),
                row("nar-2026-11-09-佐賀-04", 16 * 60 + 20),
                row("nar-2026-11-09-佐賀-06", 16 * 60 + 5)]
        details = {r["id"]: detail([horse(1, odds=None)]) for r in rows}
        self.assertEqual(
            odds_repair_targets(rows, details, self.NOW),
            ["nar-2026-11-09-佐賀-06", "nar-2026-11-09-佐賀-04",
             "nar-2026-11-09-佐賀-05"])


class SaveOddsProvenanceTest(unittest.TestCase):
    def _bank(self):
        from app import RaceDataBank
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return RaceDataBank(Path(tmp.name) / "racedb.sqlite3")

    def test_row_source_survives_the_blanket_label(self):
        bank = self._bank()
        rows = [
            {"horseNumber": 1, "winOdds": 90.8, "popularity": 9,
             "oddsSource": "NAR公式"},
            {"horseNumber": 2, "winOdds": 4.0, "popularity": 2,
             "oddsSource": "netkeiba実オッズ"},
        ]
        bank.save_odds("nar-test", rows, "NAR公式")
        latest = {z["horseNumber"]: z for z in bank.odds_latest("nar-test")}
        self.assertEqual(latest[1]["oddsSource"], "NAR公式")
        self.assertEqual(latest[2]["oddsSource"], "netkeiba実オッズ")

    def test_blanket_label_is_only_a_fallback(self):
        bank = self._bank()
        rows = [{"horseNumber": 1, "winOdds": 3.5, "popularity": 1}]
        bank.save_odds("nar-test", rows, "NAR公式")
        latest = bank.odds_latest("nar-test")
        self.assertEqual(latest[0]["oddsSource"], "NAR公式")


if __name__ == "__main__":
    unittest.main()
