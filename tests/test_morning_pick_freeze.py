"""Morning race choices are an immutable dated commitment, independent of live refresh."""
from __future__ import annotations

import unittest

from scripts.arvexq_select_prefetch_repairs import (
    _morning_from, keep_original_morning_picks,
)


class MorningPickPersistenceTests(unittest.TestCase):
    def test_old_frozen_selection_survives_reprediction_and_odds(self):
        saved = {"version": "v1", "fixedAt": "2026-10-09T08:30:00+09:00",
                 "scope": 34, "selected": True, "selectedScore": 86, "special": False}
        old = {"id": "nar-2026-10-09-大井-04", "volatility": {
            "label": "硬", "score": 20, "morningPicks": saved}}
        changed = {"id": old["id"], "volatility": {
            "label": "荒", "score": 79, "morningPicks": {
                **saved, "fixedAt": "2026-10-09T11:25:00+09:00",
                "selected": False, "selectedScore": 12,
            }}, "winOdds": 41}
        got = keep_original_morning_picks(changed, old)
        self.assertEqual(got["volatility"]["label"], "荒")
        self.assertEqual(got["volatility"]["morningPicks"], saved)
        self.assertEqual(got["environmentMeta"]["morningPicks"], saved)
        self.assertTrue(got["morningSelected"])
        self.assertEqual(got["morningPickFixedAt"], saved["fixedAt"])

    def test_frozen_zero_and_special_are_not_later_added_or_removed(self):
        saved = {"version": "v1", "fixedAt": "2026-10-09T07:45:00+09:00",
                 "scope": 34, "selected": False, "selectedScore": 0, "special": True}
        old = {"id": "nar-2026-10-09-高知-12",
               "environmentMeta": {"morningPicks": saved}}
        fresh = {"id": old["id"], "volatility": {"label": "標", "score": 40}}
        got = keep_original_morning_picks(fresh, old)
        self.assertFalse(got["morningSelected"])
        self.assertTrue(got["morningSpecial"])
        self.assertEqual(_morning_from(got), saved)

    def test_no_backfilled_selection_without_saved_original(self):
        race = {"id": "nar-2026-10-09-大井-01", "volatility": {"label": "硬"}}
        got = keep_original_morning_picks(race, None)
        self.assertIsNone(_morning_from(got))
        self.assertNotIn("morningSelected", got)


if __name__ == "__main__":
    unittest.main()
