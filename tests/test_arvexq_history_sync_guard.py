"""Unit and workflow regression coverage for the SQLite/history repair boundary.

Uses ephemeral SQLite and synthetic payloads; never rewrites user race data.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

from scripts.arvexq_sqlite_runtime_guard import install, install_app_compat

ROOT = Path(__file__).resolve().parents[1]


class SqliteHistorySyncTests(unittest.TestCase):
    def test_short_and_long_timeouts_both_preserved(self):
        original = sqlite3.connect
        try:
            install(1.0)
            with sqlite3.connect(":memory:", timeout=0.01) as db:
                self.assertGreaterEqual(db.execute("PRAGMA busy_timeout").fetchone()[0], 1000)
            with sqlite3.connect(":memory:", timeout=3.0) as db:
                self.assertGreaterEqual(db.execute("PRAGMA busy_timeout").fetchone()[0], 3000)
        finally:
            sqlite3.connect = original

    def test_legacy_result_symbol_is_only_initialized_when_absent(self):
        obj = types.SimpleNamespace()
        install_app_compat(obj)
        self.assertIsNone(obj.last3f)
        obj.last3f = "existing"
        install_app_compat(obj)
        self.assertEqual(obj.last3f, "existing")

    def test_history_workflow_uses_separate_writers_and_protected_batches(self):
        wf = (ROOT / ".github/workflows/arvexq-history-sync.yml").read_text(encoding="utf-8")
        self.assertIn('KEIBA_DATA_DIR="$RUNNER_TEMP/arvexq-history-bootstrap"', wf)
        self.assertIn("from scripts.arvexq_sqlite_runtime_guard import install", wf)
        self.assertIn("'--workers', '1'", wf)
        self.assertIn("scripts/arvexq_fetch_d1_bundle.py", wf)
        self.assertIn("scripts/arvexq_sync_batches.py", wf)
        self.assertIn("scripts/arvexq_protect_sync.py", wf)
        self.assertIn("--verify-post", wf)
        self.assertNotIn("--data-binary @history-payload.json", wf)
        self.assertNotIn('api/day?date=$HISTORY_DATE&details=1', wf)
        self.assertIn("HISTORY_NO_CHANGES", wf)
        self.assertIn("HISTORY_CHANGED_ONLY", wf)
        self.assertIn("CHANGED=$(jq '.meta.repaired_count // 0'", wf)
        repair = (ROOT / "scripts/arvexq_history_repair.py").read_text(encoding="utf-8")
        self.assertIn("changed_ids: set[str] = set()", repair)
        self.assertIn("if merged != original:", repair)
        self.assertIn('if rid in changed_ids', repair)
        self.assertIn('"repaired_count": len(changed_ids)', repair)

    def test_changed_history_sync_preserves_original_preoff_prediction(self):
        from datetime import datetime
        from arvexq.prediction.prerace_archive import JST
        from scripts.arvexq_protect_sync import guard, verify_published
        race_id = "nar-2026-10-10-大井-01"
        lock = {
            "raceId": race_id, "raceDate": "2026-10-10",
            "capturedAtEpoch": int(datetime(2026, 10, 10, 8, 0, tzinfo=JST).timestamp()),
            "horses": [{"horseNumber": 1, "mark": "◎"},
                       {"horseNumber": 2, "mark": "○"}],
            "frozen": True,
        }
        old = {"id": race_id, "date": "2026-10-10", "startTime": "13:00",
               "preRacePrediction": lock,
               "preRaceBet": {"fixedAt": "2026-10-10T08:00:00+09:00",
                              "decision": "見送り", "items": []}}
        changed = {"id": race_id, "date": old["date"], "startTime": old["startTime"],
                   "result": {"status": "確定"}}
        payload = guard({"details": [changed]}, read=lambda base, rid: old, base="https://unit.invalid")
        published = payload["details"][0]
        self.assertEqual(published["preRacePrediction"], lock)
        self.assertEqual(published["preRaceBet"], old["preRaceBet"])
        self.assertEqual(published["result"]["status"], "確定")
        self.assertEqual(verify_published(payload, base="https://unit.invalid",
                           read=lambda base, rid: published), [race_id])
        with self.assertRaisesRegex(RuntimeError, "D1_SEAL_POST_VERIFY_MISMATCH"):
            verify_published(payload, base="https://unit.invalid",
                             read=lambda base, rid: changed)

    def test_split_batched_history_payload_retains_race_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            payload = {
                "summaries": [{"id": "race1"}, {"id": "race2"}, {"id": "race3"}],
                "details": [{"id": "race1", "horses": [{"horseNumber": 1}]},
                            {"id": "race2", "horses": [{"horseNumber": 2}]}],
                "meta": {"sync_date": "2026-10-08", "race_count": 3},
            }
            infile = home / "payload.json"
            infile.write_text(json.dumps(payload), encoding="utf-8")
            subprocess.run([
                sys.executable, str(ROOT / "scripts/arvexq_sync_batches.py"),
                "--input", str(infile), "--out-dir", str(home / "batches"),
            ], cwd=str(ROOT), check=True, capture_output=True, text=True, timeout=15)
            bodies = [json.loads(p.read_text(encoding="utf-8"))
                      for p in sorted((home / "batches").glob("batch-*.json"))]
            self.assertEqual(len(bodies), 3)
            self.assertTrue(all(len(body.get("details", [])) <= 1 for body in bodies))
            self.assertEqual(sorted(x["id"] for body in bodies for x in body.get("summaries", [])),
                             ["race1", "race2", "race3"])
            self.assertTrue(all(body["meta"]["sync_date"] == "2026-10-08" for body in bodies))


if __name__ == "__main__":
    unittest.main()
