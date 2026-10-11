"""Regression checks for immutable D1 input gates and one canonical result updater."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from arvexq.pipeline.persisted_inputs import verify_persisted_facts, may_create_prerace_prediction
from arvexq.results.day_index import restore_if_empty

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-12"
RID = f"nar-{DAY}-盛岡-01"


def card():
    return {
        "id": RID, "date": DAY, "track": "盛岡", "raceNumber": 1,
        "startTime": "10:00", "fieldSize": 2,
        "horses": [
            {"horseNumber": 1, "name": "馬A",
             "allPastRuns": [{"date": "2026-10-01", "finish": 2},
                             {"date": "2026-09-20", "finish": 1}]},
            {"horseNumber": 2, "name": "馬B",
             "recentRaces": [{"date": "2026-10-02", "finish": 3}]},
        ],
    }


def source():
    return {"summaries": [{"id": RID}], "details": [card()]}


def readback():
    return {"races": [{"id": RID}], "details": [card()]}


class PersistedInputTests(unittest.TestCase):
    def test_verified_round_trip_accepts_same_career(self):
        self.assertEqual(verify_persisted_facts(source(), readback()), [])

    def test_d1_missing_summary_is_not_a_saved_fact(self):
        saved = readback()
        saved["races"] = []
        self.assertIn(f"{RID}:summary-not-saved", verify_persisted_facts(source(), saved))

    def test_d1_truncated_career_blocks_analysis(self):
        saved = readback()
        saved["details"][0]["horses"][0]["allPastRuns"].pop()
        self.assertTrue(any("allPastRuns-truncated" in x
                            for x in verify_persisted_facts(source(), saved)))

    def test_d1_wrong_runner_blocks_analysis(self):
        saved = readback()
        saved["details"][0]["horses"][0]["name"] = "別の馬"
        self.assertTrue(any("horse-identities-changed" in x
                            for x in verify_persisted_facts(source(), saved)))

    def test_no_retroactive_prediction(self):
        tz = timezone(timedelta(hours=9))
        self.assertTrue(may_create_prerace_prediction(card(),
                        datetime(2026, 10, 12, 9, 59, tzinfo=tz)))
        self.assertFalse(may_create_prerace_prediction(card(),
                         datetime(2026, 10, 12, 10, 0, tzinfo=tz)))

    def test_result_day_recovers_only_canonical_verified_archive(self):
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / (DAY + ".json")
            race = {"id": RID, "date": DAY, "track": "盛岡", "raceNumber": 1}
            archive.write_text(json.dumps({
                "version": "arvexq-static-entry-v1", "date": DAY, "races": [race]
            }, ensure_ascii=False), encoding="utf-8")
            out, method = restore_if_empty({"date": DAY, "races": [], "details": []}, DAY, archive)
            self.assertEqual(method, "verified-canonical-racecard-archive")
            self.assertEqual(out["races"], [race])
            preserved, method = restore_if_empty({"date": DAY, "races": [race], "details": []}, DAY, archive)
            self.assertEqual(method, "d1")
            self.assertEqual(preserved["races"], [race])
            archive.write_text(json.dumps({
                "version": "arvexq-static-entry-v1", "date": DAY,
                "races": [{**race, "id": "nar-2026-10-11-盛岡-01"}]
            }, ensure_ascii=False), encoding="utf-8")
            invalid, method = restore_if_empty({"races": [], "details": []}, DAY, archive)
            self.assertEqual(invalid["races"], [])
            self.assertEqual(method, "incomplete-racecard-archive")

    def test_workflow_stage_order_and_result_restore(self):
        prefetch = (ROOT / ".github/workflows/arvexq-prefetch.yml").read_text(encoding="utf-8")
        steps = [
            "Collect racecards and full careers without running predictions",
            "Persist collected facts using the existing D1 sync pipeline",
            "Read D1 facts back and require identical horse/history evidence",
            "Analyze only persisted D1 data and prepare original marks and bets",
            "Freeze morning selected and special predictions for all races",
            "Push prepared day repairs to D1 in safe batches",
        ]
        positions = [prefetch.index(x) for x in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("'--phase', 'collect'", prefetch)
        self.assertIn("'--phase', 'analyze'", prefetch)
        self.assertIn("D1_STORED_EVIDENCE_VERIFIED", prefetch)
        result = (ROOT / ".github/workflows/arvexq-result-repair.yml").read_text(encoding="utf-8")
        self.assertIn("--allow-empty-day", result)
        self.assertIn("arvexq_restore_result_day.py", result)


if __name__ == "__main__":
    unittest.main()
