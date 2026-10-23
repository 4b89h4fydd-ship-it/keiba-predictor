"""Read-only post-capture coverage never invents improvement from missing frozen data."""
from __future__ import annotations

import json
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from scripts.arvexq_nar_context_coverage import REQUIRED_SCHEMA, audit_rows, main


def rows(race_id: str, schema: str = REQUIRED_SCHEMA, context: bool = True):
    return [{
        "raceId": race_id,
        "circuit": "地方",
        "date": "2026-10-21",
        "track": "高知",
        "featureHash": "original-hash-" + race_id,
        "schemaVersion": schema,
        "horseNumber": num,
        "labelWin": int(num == 2),
        "features": {
            **({"nar::pace::front_rate_w5": (num - 1) / 3} if context else {}),
            **({"nar::trip::wideTrip_rate_w5": 0.5} if num == 1 and context else {}),
            "history::all::w5::finish_quality::mean": 0.5,
        },
    } for num in (1, 2, 3)]


class FrozenContextCoverageTest(unittest.TestCase):
    def test_unavailable_real_features_report_no_accuracy_or_roi(self):
        outcome = audit_rows(rows("past", "old-v2", False))
        self.assertEqual(outcome["newSchemaRaces"], 0)
        self.assertEqual(outcome["exclusions"]["old_or_mixed_schema"], 1)
        self.assertEqual(outcome["status"], "no_new_frozen_context_features")
        self.assertIsNone(outcome["measuredAccuracy"])
        self.assertIsNone(outcome["measuredROI"])

    def test_new_snapshot_race_family_coverage_is_counted(self):
        outcome = audit_rows(rows("new"))
        self.assertEqual(outcome["newSchemaRaces"], 1)
        self.assertEqual(outcome["newSchemaHorseRows"], 3)
        self.assertEqual(outcome["contextHorseRows"], 3)
        self.assertEqual(outcome["families"]["pace"]["races"], 1)
        self.assertEqual(outcome["families"]["pace"]["horses"], 3)
        self.assertEqual(outcome["families"]["trip"]["horses"], 1)
        self.assertEqual(outcome["families"]["trip"]["horseCoveragePct"], 33.33)
        self.assertEqual(outcome["families"]["bias"]["horses"], 0)
        self.assertIsNone(outcome["measuredAccuracy"])

    def test_reject_partial_winner_mixed_hash_and_duplicate_field(self):
        invalid = [
            rows("partial")[:2],
            [dict(r, labelWin=0) for r in rows("no-winner")],
            [dict(r, featureHash="conflict") if i == 2 else r for i, r in enumerate(rows("mismatch"))],
            rows("duplicate") + [dict(rows("duplicate")[0])],
        ]
        for group in invalid:
            with self.subTest(race=group[0]["raceId"]):
                outcome = audit_rows(group)
                self.assertEqual(outcome["newSchemaRaces"], 0)
                self.assertEqual(outcome["exclusions"]["incomplete_or_ambiguous_race"], 1)

    def test_banei_and_jra_not_audit_denominator(self):
        group = rows("test")
        group[0]["track"] = "帯広"
        group[1]["circuit"] = "中央"
        outcome = audit_rows(group)
        self.assertEqual(outcome["newSchemaRaces"], 0)
        self.assertEqual(outcome["exclusions"]["banei"], 1)
        self.assertEqual(outcome["exclusions"]["non_nar_or_invalid"], 1)

    def test_jsonl_input_is_read_only(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "official-frozen-rows.jsonl"
            data = rows("new")
            target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data), encoding="utf-8")
            before = target.read_bytes()
            self.assertEqual(main([str(target), "--format", "jsonl"]), 0)
            self.assertEqual(before, target.read_bytes())


if __name__ == "__main__":
    unittest.main()
