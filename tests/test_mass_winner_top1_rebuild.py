"""Regression coverage for evidence-complete winner-top1 research training.

No production prediction, network access or score weighting is activated.
"""
import unittest
import json
import sqlite3
from copy import deepcopy
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from arvexq.prediction.mass_training_dataset import rows_from_frozen_snapshot
from arvexq.prediction.mass_training_store import frozen_training_rows_from_detail, load_frozen_training_rows
from arvexq.prediction.mass_feature_transport import _feature_hash
from arvexq.ingest.full_snapshot_codec import pack_detail
from arvexq.prediction.mass_model_training import _race_winner_top1, _training_circuit, prepare_head_rows


class RebuiltWinnerTop1TrainingTests(unittest.TestCase):
    def snapshot(self):
        return {
            "raceId": "nar-2026-10-21-門別-12",
            "date": "2026-10-21",
            "circuit": "地方",
            "track": "門別",
            "raceNumber": 12,
            "horseCount": 3,
            "rows": [
                {"horseNumber": n, "name": str(n), "features": {"static::age": 5.0 + n}}
                for n in (1, 2, 3)
            ],
        }

    def result(self):
        return {"finishers": [
            {"horseNumber": 1, "finish": 2},
            {"horseNumber": 2, "finish": 1},
            {"horseNumber": 3, "finish": 3},
        ]}

    def eligible_detail(self):
        snapshot = self.snapshot()
        snapshot["featureHash"] = _feature_hash(snapshot)
        return {
            "id": snapshot["raceId"], "date": snapshot["date"],
            "circuit": snapshot["circuit"],
            "massFeatureSnapshot": snapshot,
            "massFeatureHash": snapshot["featureHash"],
            "result": {"status": "確定", **self.result()},
        }

    def test_direct_snapshot_hash_is_actually_recomputed(self):
        good = self.eligible_detail()
        self.assertEqual(len(frozen_training_rows_from_detail(good)), 3)
        tampered = deepcopy(good)
        tampered["massFeatureSnapshot"]["rows"][0]["features"]["static::age"] = 999.0
        self.assertEqual(frozen_training_rows_from_detail(tampered), [])

    def test_direct_snapshot_race_identity_and_declared_lock_must_agree(self):
        good = self.eligible_detail()
        self.assertEqual(len(frozen_training_rows_from_detail(good)), 3)
        for key, value in (("id", "nar-2026-10-21-門別-11"),
                           ("date", "2026-10-20"), ("circuit", "中央"),
                           ("massFeatureHash", "different-hash")):
            mismatch = deepcopy(good)
            mismatch[key] = value
            self.assertEqual(frozen_training_rows_from_detail(mismatch), [], key)
        wrong_lock = deepcopy(good)
        wrong_lock["preRacePrediction"] = {"massFeatureHash": "different-hash"}
        self.assertEqual(frozen_training_rows_from_detail(wrong_lock), [])

    def test_explicitly_unverified_snapshot_remains_ineligible(self):
        good = self.eligible_detail()
        flagged = deepcopy(good)
        flagged["verifiedForTraining"] = False
        self.assertEqual(frozen_training_rows_from_detail(flagged), [])
        legacy = deepcopy(good)
        legacy["massFeatureArchive"] = {
            "originHashVerified": False, "featureHash": good["massFeatureHash"]
        }
        self.assertEqual(frozen_training_rows_from_detail(legacy), [])

    def test_existing_full_payload_storage_recovers_frozen_training_rows(self):
        # The thin D1 display projection omits nested massFeatureSnapshot.
        # SQLite training must unpack the full original, not interpret the
        # displayed index as proof that the original snapshot is missing.
        detail = self.eligible_detail()
        packed = pack_detail(detail)
        self.assertNotIn("massFeatureSnapshot", packed)
        rows = frozen_training_rows_from_detail(packed)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["horseNumber"] for r in rows], [1, 2, 3])
        self.assertEqual(sum(r["labelWin"] for r in rows), 1)

        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "races.sqlite3"
            con = sqlite3.connect(db)
            try:
                con.execute(
                    "CREATE TABLE race_snapshots (race_id TEXT, race_date TEXT, circuit TEXT, payload TEXT)"
                )
                con.execute("INSERT INTO race_snapshots VALUES (?, ?, ?, ?)",
                            (detail["id"], detail["date"], detail["circuit"],
                             json.dumps(packed, ensure_ascii=False)))
                con.commit()
            finally:
                con.close()
            original = load_frozen_training_rows(db)
            self.assertEqual(len(original), 3)
            self.assertEqual([r["featureHash"] for r in original],
                             [detail["massFeatureHash"]] * 3)

    def test_corrupt_full_payload_does_not_enter_training(self):
        packed = pack_detail(self.eligible_detail())
        bad = deepcopy(packed)
        bad["arvexqFullPayload"]["sha256"] = "0" * 64
        self.assertEqual(frozen_training_rows_from_detail(bad), [])
        bad = deepcopy(packed)
        bad["arvexqFullPayload"]["gzipBase64"] = "not-base64!"
        self.assertEqual(frozen_training_rows_from_detail(bad), [])

    def test_display_index_cannot_forge_results_over_original_payload(self):
        detail = self.eligible_detail()
        detail["result"]["status"] = "速報"
        packed = pack_detail(detail)
        packed["result"]["status"] = "確定"
        self.assertEqual(frozen_training_rows_from_detail(packed), [])

    def test_archive_legacy_without_outer_circuit_remains_eligible(self):
        detail = self.eligible_detail()
        detail.pop("circuit")
        self.assertEqual(len(frozen_training_rows_from_detail(detail)), 3)

    def test_sqlite_index_must_match_frozen_id_date_and_circuit(self):
        detail = self.eligible_detail()
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "races.sqlite3"
            connection = sqlite3.connect(db)
            try:
                connection.execute(
                    "CREATE TABLE race_snapshots (race_id TEXT, race_date TEXT, circuit TEXT, payload TEXT)"
                )
                payload = json.dumps(detail, ensure_ascii=False)
                for rid, day, circuit in (
                    (detail["id"], detail["date"], "地方"),
                    ("nar-2026-10-21-門別-11", detail["date"], "地方"),
                    (detail["id"], "2026-10-20", "地方"),
                    (detail["id"], detail["date"], "中央"),
                ):
                    connection.execute("INSERT INTO race_snapshots VALUES (?, ?, ?, ?)",
                                       (rid, day, circuit, payload))
                connection.commit()
            finally:
                connection.close()
            rows = load_frozen_training_rows(db)
            self.assertEqual(len(rows), 3)
            self.assertEqual({r["raceId"] for r in rows}, {detail["id"]})

    def test_duplicate_official_finish_record_fails_closed(self):
        snap = self.snapshot()
        result = self.result()
        result["finishers"].append(dict(result["finishers"][1]))
        self.assertEqual(rows_from_frozen_snapshot(snap, result), [])
        # A conflicting duplicate is just as invalid as an identical duplicate.
        result["finishers"][-1]["finish"] = 3
        self.assertEqual(rows_from_frozen_snapshot(snap, result), [])

    def test_current_race_outcome_feature_leakage_rejected(self):
        # Only the outcome joined after freezing may contain race labels.
        for key in ("finish", "rank", "result", "winner", "labelWin",
                    "labelTop2", "labelTop3", "payouts"):
            snap = self.snapshot()
            snap["rows"][1]["features"][key] = 1
            self.assertEqual(rows_from_frozen_snapshot(snap, self.result()), [], key)
        historical = self.snapshot()
        historical["rows"][1]["features"]["history::2026-10-01::finish_quality"] = 0.7
        self.assertEqual(len(rows_from_frozen_snapshot(historical, self.result())), 3)

    def test_complete_frozen_field_yields_exact_labels(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(row["labelWin"] for row in rows), 1)
        self.assertEqual(_race_winner_top1(rows, [0.2, 0.8, 0.1])["winnerTop1Rate"], 1.0)

    def test_incomplete_result_does_not_create_easier_training_race(self):
        incomplete = {"finishers": self.result()["finishers"][:2]}
        self.assertEqual(rows_from_frozen_snapshot(self.snapshot(), incomplete), [])

    def test_duplicate_or_ambiguous_frozen_field_does_not_train(self):
        snap = self.snapshot()
        snap["rows"][2]["horseNumber"] = 2
        self.assertEqual(rows_from_frozen_snapshot(snap, self.result()), [])
        snap2 = self.snapshot()
        snap2["horseCount"] = 4
        self.assertEqual(rows_from_frozen_snapshot(snap2, self.result()), [])

    def test_unresolved_winner_does_not_train(self):
        results = self.result()
        results["finishers"][1]["finish"] = 2
        self.assertEqual(rows_from_frozen_snapshot(self.snapshot(), results), [])

    def test_central_local_training_isolated(self):
        self.assertEqual(_training_circuit([{"circuit": "中央"}, {"circuit": "jra"}]), "jra")
        self.assertEqual(_training_circuit([{"circuit": "地方"}, {"circuit": "nar"}]), "nar")
        with self.assertRaises(ValueError):
            _training_circuit([{"circuit": "中央"}, {"circuit": "地方"}])
        with self.assertRaises(ValueError):
            _training_circuit([{"circuit": "unknown"}])

    def test_winner_top1_has_explicit_coverage_and_tie_exclusion(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        metrics = _race_winner_top1(rows, [0.2, 0.8, 0.1])
        self.assertEqual((metrics["cohortRaces"], metrics["scoredRaces"], metrics["winnerTop1Hits"]), (1, 1, 1))
        self.assertEqual(metrics["byCircuit"]["地方"]["hits"], 1)
        tied = _race_winner_top1(rows, [0.8, 0.8, 0.1])
        self.assertEqual(tied["scoredRaces"], 0)
        self.assertEqual(tied["tiedPredictionRaces"], 1)
        self.assertIsNone(tied["winnerTop1Rate"])
        with self.assertRaises(ValueError):
            _race_winner_top1(rows, [0.2, 0.8])

    def test_invalid_labelled_holdout_is_not_scored(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        rows[0]["horseNumber"] = rows[1]["horseNumber"]
        metrics = _race_winner_top1(rows, [0.1, 0.8, 0.1])
        self.assertEqual(metrics["scoredRaces"], 0)
        self.assertEqual(metrics["incompleteOrInvalidRaces"], 1)

    def test_missing_horse_features_drops_whole_race_not_only_that_horse(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        for head in ("ability", "win", "podium"):
            self.assertEqual(len(prepare_head_rows(rows, head)), 3)
            partial = [dict(row) for row in rows]
            partial[2]["features"] = {"market::popularity": 3.0}
            self.assertEqual(prepare_head_rows(partial, head), [])

    def test_complete_races_survive_when_another_race_is_incomplete(self):
        rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
        other = [dict(row, raceId="nar-2026-10-20-門別-11") for row in rows]
        other[0]["features"] = {}
        prepared = prepare_head_rows(rows + other, "win")
        self.assertEqual(len(prepared), 3)
        self.assertEqual({row["raceId"] for row in prepared}, {rows[0]["raceId"]})

    def test_existing_train_cli_refuses_mixed_circuits_and_mismatch(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "train_mass_models.py"
        with TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "frozen.jsonl"
            rows = rows_from_frozen_snapshot(self.snapshot(), self.result())
            for second_circuit, wanted, expected in (
                ("中央", "nar", "mixed or unlabelled"),
                ("地方", "jra", "requested jra"),
            ):
                mixed = [dict(row) for row in rows]
                mixed[0]["circuit"] = second_circuit
                dataset.write_text(
                    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in mixed),
                    encoding="utf-8",
                )
                proc = subprocess.run(
                    [sys.executable, str(script), str(dataset), str(Path(tmp) / "model"),
                     str(Path(tmp) / "runtime"), "--circuit", wanted],
                    capture_output=True, text=True, timeout=20,
                )
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(expected, proc.stderr + proc.stdout)
            self.assertFalse((Path(tmp) / "model").exists())
            self.assertFalse((Path(tmp) / "runtime").exists())


if __name__ == "__main__":
    unittest.main()
