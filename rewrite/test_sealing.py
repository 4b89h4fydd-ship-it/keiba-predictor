"""Tests for the pre-off sealing store."""
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rewrite.output.sealing import SealCollisionError, SealStore

NOW = datetime(2026, 10, 28, 1, 0, tzinfo=timezone.utc)
START = datetime(2026, 10, 28, 3, 20, tzinfo=timezone.utc)
PAYLOAD = {"kind": "arvexq-sealed-forecast", "racePayload": {"id": "x"}, "marks": ["◎"]}


class SealingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "seals.sqlite3"
        self.store = SealStore(self.path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_seal_read_round_trip_pre_off(self):
        receipt = self.store.seal("r1", "m1", PAYLOAD, scheduled_start=START, now=NOW)
        self.assertTrue(receipt.pre_off)
        record = self.store.read("r1", "m1")
        self.assertEqual(record["payload"], PAYLOAD)
        self.assertEqual(record["receipt"]["payload_sha256"], receipt.payload_sha256)
        self.assertTrue(record["receipt"]["pre_off"])

    def test_seal_after_start_is_not_pre_off(self):
        receipt = self.store.seal(
            "r1", "m1", PAYLOAD, scheduled_start=START,
            now=START + timedelta(minutes=1),
        )
        self.assertFalse(receipt.pre_off)

    def test_idempotent_same_payload(self):
        first = self.store.seal("r1", "m1", PAYLOAD, scheduled_start=START, now=NOW)
        second = self.store.seal(
            "r1", "m1", PAYLOAD, scheduled_start=START,
            now=NOW + timedelta(hours=1),
        )
        self.assertEqual(first.payload_sha256, second.payload_sha256)
        self.assertEqual(second.sealed_at, first.sealed_at)

    def test_collision_on_different_payload(self):
        self.store.seal("r1", "m1", PAYLOAD, scheduled_start=START, now=NOW)
        with self.assertRaises(SealCollisionError):
            self.store.seal("r1", "m1", {"kind": "other"}, scheduled_start=START, now=NOW)

    def test_rows_are_immutable(self):
        self.store.seal("r1", "m1", PAYLOAD, scheduled_start=START, now=NOW)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db:
                self.store.db.execute(
                    "UPDATE sealed_forecasts SET sealed_at='x' WHERE race_id='r1'")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db:
                self.store.db.execute(
                    "DELETE FROM sealed_forecasts WHERE race_id='r1'")

    def test_read_detects_hash_mismatch(self):
        raw = sqlite3.connect(self.path)
        raw.execute(
            "INSERT INTO sealed_forecasts VALUES(?,?,?,?,?,?)",
            ("bad", "m1", b'{"kind":"x"}', "0" * 64,
             NOW.isoformat(), START.isoformat()),
        )
        raw.commit()
        raw.close()
        with self.assertRaises(ValueError):
            self.store.read("bad", "m1")


if __name__ == "__main__":
    unittest.main()
