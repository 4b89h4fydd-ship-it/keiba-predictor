"""Banei (Obihiro) exclusion is one shared test on every route.

Before the unification, the rewrite publisher checked only the
track string (a missing track let the race through), the D1 sync
guard had no check at all, and the prefetch analyze stage filtered
its rows but not its details. These tests pin the shared helper and
the sync guard's behaviour so the weak spellings cannot return.
"""
from __future__ import annotations

import unittest

from arvexq.ingest.banei import is_banei


class IsBaneiTests(unittest.TestCase):
    def test_track_spellings(self):
        self.assertTrue(is_banei("帯広", "nar-2026-11-10-帯広-01"))
        self.assertTrue(is_banei("帯広ば", None))
        self.assertTrue(is_banei("帯広ばんえい", None))

    def test_race_id_embedding(self):
        self.assertTrue(is_banei(None, "nar-2026-11-10-帯広-01"))
        self.assertTrue(is_banei("", "nar-2026-11-10-帯広ば-01"))
        self.assertTrue(is_banei(None, "帯広-01"))

    def test_missing_track_falls_back_to_id(self):
        # The publisher's old check passed this race through.
        self.assertTrue(is_banei(None, "nar-2026-11-11-帯広-03"))

    def test_regular_races_are_not_banei(self):
        self.assertFalse(is_banei("名古屋", "nar-2026-11-10-名古屋-01"))
        self.assertFalse(is_banei("東京", "jra-2026-11-10-東京-11"))
        self.assertFalse(is_banei(None, None))
        self.assertFalse(is_banei("", ""))


class SyncGuardTests(unittest.TestCase):
    def test_guard_drops_banei_details(self):
        from scripts.arvexq_protect_sync import guard

        body = {"details": [
            {"id": "nar-2026-11-11-帯広-01", "track": "帯広"},
            {"id": "nar-2026-11-11-名古屋-01", "track": "名古屋"},
            {"id": "nar-2026-11-11-帯広ば-02"},
        ]}
        out = guard(body, read=lambda base, rid: None, base="test://")
        kept = [d["id"] for d in out["details"]]
        self.assertEqual(kept, ["nar-2026-11-11-名古屋-01"])


if __name__ == "__main__":
    unittest.main()
