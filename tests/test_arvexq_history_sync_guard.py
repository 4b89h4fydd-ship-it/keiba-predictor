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
