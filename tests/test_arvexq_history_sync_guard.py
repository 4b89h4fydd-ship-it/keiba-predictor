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
        self.assertIn("--allow-empty-day", wf)
        self.assertIn("HISTORY_INITIAL_PUBLICATION=1", wf)
        self.assertIn("--initial-publication", wf)
        self.assertIn('test "$PUBLISHED" -eq "$RACES"', wf)
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

    def test_old_frozen_feature_hash_is_preserved_but_not_trained(self):
        # A legacy D1 race may contain genuine historical feature bytes with
        # a hash from an older serializer. Enriching results or career history
        # must not forge a fresh featureHash or overwrite the pre-off forecast.
        from arvexq.prediction.mass_feature_snapshot import _stable_hash
        from arvexq.ingest.full_snapshot_codec import unpack_detail
        from arvexq.prediction.mass_training_store import frozen_training_rows_from_detail
        frozen = {
            "raceId": "nar-2026-09-15-園田-03", "date": "2026-09-15",
            "horseCount": 1, "rows": [{"horseNumber": 1, "features": {"pace": .6}}]
        }
        frozen["featureHash"] = _stable_hash(frozen)
        original_hash = frozen["featureHash"]
        # Simulate old historical source rows differing from their declared hash.
        frozen["rows"][0]["features"]["pace"] = .7
        prediction = {"modelVersion": "frozen-before-off", "horseNumber": 1}
        detail = {
            "id": frozen["raceId"], "date": frozen["date"], "circuit": "地方",
            "horses": [{"horseNumber": 1, "name": "保存馬"}],
            "preRacePrediction": prediction,
            "massFeatureSnapshot": frozen, "massFeatureHash": original_hash,
            "result": {"status": "確定", "finishers": [{"horseNumber": 1, "finish": 1}]}
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def invoke(source):
                payload = root / "source.json"
                payload.write_text(json.dumps({"meta": {"source": source},
                                              "details": [detail]}, ensure_ascii=False), encoding="utf-8")
                dest = root / "batch"
                return subprocess.run([sys.executable, str(ROOT / "scripts/arvexq_sync_batches.py"),
                                       "--input", str(payload), "--out-dir", str(dest)],
                                      cwd=str(ROOT), capture_output=True, text=True,
                                      timeout=30), dest
            bad, _ = invoke("normal-live-unknown")
            self.assertNotEqual(bad.returncode, 0, "Never silently bypass feature origin checks")
            good, output = invoke("github-actions-history-missing-only-v2")
            self.assertEqual(good.returncode, 0, good.stderr[-2000:])
            self.assertIn("MASS_FEATURE_LEGACY_UNVERIFIED", good.stdout)
            batch = json.loads((output / "batch-0001.json").read_text(encoding="utf-8"))
            saved = unpack_detail(batch["details"][0])
            self.assertEqual(saved["preRacePrediction"], prediction)
            self.assertEqual(saved["massFeatureHash"], original_hash)
            self.assertEqual(saved["massFeatureArchive"]["featureHash"], original_hash)
            self.assertIs(saved["massFeatureArchive"]["originHashVerified"], False)
            self.assertEqual(saved["massFeatureArchive"]["originStatus"],
                             "legacy-unverified-not-for-training")
            self.assertEqual(frozen_training_rows_from_detail(saved), [])

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
            proc = subprocess.run([
                sys.executable, str(ROOT / "scripts/arvexq_sync_batches.py"),
                "--input", str(infile), "--out-dir", str(home / "batches"),
            ], cwd=str(ROOT), check=False, capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0,
                             "Batch CLI failed stdout="+proc.stdout[-2000:]+" stderr="+proc.stderr[-2500:])
            bodies = [json.loads(p.read_text(encoding="utf-8"))
                      for p in sorted((home / "batches").glob("batch-*.json"))]
            self.assertEqual(len(bodies), 3)
            self.assertTrue(all(len(body.get("details", [])) <= 1 for body in bodies))
            self.assertEqual(sorted(x["id"] for body in bodies for x in body.get("summaries", [])),
                             ["race1", "race2", "race3"])
            self.assertTrue(all(body["meta"]["sync_date"] == "2026-10-08" for body in bodies))



class HistoricalForecastRevisionReceiptTests(unittest.TestCase):
    """Archived old receipts must remain immutable without the removed model."""

    @staticmethod
    def _old_detail():
        from hashlib import sha256
        revision = {
            "version": "arvexq-forecast-revision-v1",
            "raceId": "nar-2026-10-19-大井-01",
            "raceDate": "2026-10-19",
            "predictionStatus": "archived",
        }
        digest = sha256(json.dumps(revision, sort_keys=True,
                                   ensure_ascii=False, separators=(",", ":"),
                                   allow_nan=False).encode()).hexdigest()
        revision["revisionId"] = digest
        revision["createdAt"] = "2026-10-19T04:00:00+00:00"
        return {"id": revision["raceId"], "date": revision["raceDate"],
                "preRacePrediction": {"original": "sealed"},
                "preRaceBet": {"original": "bet"},
                "forecastRevisions": [revision],
                "currentForecastRevisionId": digest}

    def test_live_sync_preserves_existing_revision_receipts_and_preoff_original(self):
        from copy import deepcopy
        from scripts.arvexq_protect_sync import protect_detail
        old = self._old_detail()
        original = deepcopy(old)
        result = protect_detail(old, {"id": old["id"], "date": old["date"],
                                      "preRacePrediction": old["preRacePrediction"],
                                      "preRaceBet": old["preRaceBet"]})
        self.assertEqual(old, original)
        self.assertEqual(result["forecastRevisions"], original["forecastRevisions"])
        self.assertEqual(result["currentForecastRevisionId"],
                         original["currentForecastRevisionId"])
        self.assertEqual(result["preRacePrediction"], original["preRacePrediction"])
        self.assertEqual(result["preRaceBet"], original["preRaceBet"])

    def test_invalid_or_replaced_archive_chain_is_refused_not_silently_erased(self):
        from scripts.arvexq_protect_sync import protect_detail
        old = self._old_detail()
        with self.assertRaisesRegex(ValueError, "prefix changed"):
            protect_detail(old, {"id": old["id"],
                                 "forecastRevisions": [{"revisionId": "tampered"}]})
        with self.assertRaisesRegex(ValueError, "pointer is invalid"):
            protect_detail({}, {"forecastRevisions": [],
                                "currentForecastRevisionId": "not-in-chain"})


    def test_initial_publication_sends_all_originals_without_modification(self):
        from scripts.arvexq_history_repair import select_publication_ids
        import copy
        ids=['nar-01','nar-02','nar-03']
        old={rid:{'id':rid,'preRacePrediction':{'original':'frozen'}}
             for rid in ids}
        before=copy.deepcopy(old)
        self.assertEqual(select_publication_ids(ids,old,{'nar-01'},False),
                         ['nar-01'])
        self.assertEqual(select_publication_ids(ids,old,{'nar-01'},True),
                         ids)
        self.assertEqual(old,before)
        with self.assertRaisesRegex(ValueError,'cold-start source details missing'):
            select_publication_ids(ids,{'nar-01':old['nar-01']},
                                   {'nar-01'},True)


if __name__ == "__main__":
    unittest.main()
