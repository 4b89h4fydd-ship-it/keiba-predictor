"""Racecard delivery must never be held hostage by isolated AI/roster failures."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import arvexq_select_prefetch_repairs as repair


def race(rid: str, numbers: tuple[int, ...], ai: bool = True) -> dict:
    return {
        "id": rid,
        "track": "大井",
        "date": "2026-10-08",
        "horses": [{"horseNumber": n, "name": f"馬{n}"} for n in numbers],
        "preparedMeta": {"diagnosisReady": ai},
    }


class PrefetchRacecardDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.id = "nar-2026-10-08-大井-04"

    def test_partial_roster_with_ai_is_still_a_repair(self) -> None:
        prepared = race(self.id, (1, 2, 3, 4))
        current = race(self.id, (1, 2))
        self.assertTrue(repair.rich(current))
        self.assertEqual(repair.repair_reason(prepared, current), "roster_incomplete")

    def test_missing_ai_does_not_make_the_roster_unavailable(self) -> None:
        prepared = race(self.id, (1, 2, 3, 4), ai=False)
        self.assertEqual(len(repair.named_roster(prepared)), 4)
        self.assertEqual(repair.repair_reason(prepared, None), "missing")

    def test_existing_complete_snapshot_unchanged(self) -> None:
        prepared = race(self.id, (1, 2, 3))
        existing = race(self.id, (1, 2, 3))
        self.assertEqual(repair.repair_reason(prepared, existing), "")

    def test_missing_analysis_can_be_repaired_without_erasing_roster(self) -> None:
        prepared = race(self.id, (1, 2, 3))
        existing = race(self.id, (1, 2, 3), ai=False)
        self.assertEqual(repair.repair_reason(prepared, existing), "thin")

    def test_repair_selection_does_not_erase_known_horses(self) -> None:
        rid2 = "nar-2026-10-08-大井-05"
        rid3 = "nar-2026-10-08-園田-03"
        source = [
            race(self.id, (1, 2, 3), ai=True),
            race(rid2, (1, 2), ai=True),
            race(rid3, (1, 2), ai=False),
        ]
        current = [
            race(self.id, (1, 2), ai=True),
            race(rid2, (1, 2, 3), ai=True),
        ]
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            prepared_file = directory / "prepared.json"
            current_file = directory / "current.json"
            output_file = directory / "out.json"
            report_file = directory / "report.json"
            prepared_file.write_text(json.dumps({
                "summaries": [{"id": d["id"]} for d in source],
                "details": source,
                "meta": {"race_count": 3},
            }, ensure_ascii=False), encoding="utf-8")
            current_file.write_text(json.dumps({"details": current}, ensure_ascii=False), encoding="utf-8")
            argv = ["prefetch", "--prepared", str(prepared_file), "--current", str(current_file),
                    "--out", str(output_file), "--report", str(report_file)]
            with patch.object(sys, "argv", argv):
                self.assertEqual(repair.main(), 0)
            payload = json.loads(output_file.read_text(encoding="utf-8"))
            report = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual({d["id"] for d in payload["details"]}, {self.id, rid3})
            self.assertEqual(len(payload["summaries"]), 3)
            self.assertEqual(report["repair_count"], 2)
            self.assertIn("source_roster_missing_known_horses",
                          [r["reason"] for r in report["repairs"]])

    def test_pipeline_still_publishes_when_analysis_fails(self) -> None:
        workflow = Path(".github/workflows/arvexq-prefetch.yml").read_text(encoding="utf-8")
        self.assertIn("proceeding to D1 repair", workflow)
        self.assertIn("FAILED_BATCHES=$((FAILED_BATCHES + 1))", workflow)
        self.assertIn("D1_MISSING_CARDS", workflow)
        guard = workflow.split('if [ "$MISSING_CARD" -gt 0 ] || [ "$MISSING_ANALYSIS" -gt 0 ]; then', 1)[1].split("\n          fi", 1)[0]
        self.assertNotIn("exit 1", guard)


if __name__ == "__main__":
    unittest.main()
