"""Pre-off sealing of forecasts: append-only, hash-verified records.

A sealed record is the evidence that a prediction existed before a
race started: the exact payload the display layer would show, hashed
with SHA-256 over its canonical JSON, stored with the seal time and
the race's scheduled start. Table rows cannot be updated or deleted
(SQLite triggers enforce it), and sealing the same race under the
same model key with a different payload is a collision error, never
a silent overwrite.

Odds recorded alongside are the win odds present in the source data
at prediction time, with the source fetch time — the like-for-like
market comparison point for later validation.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def canonical(payload: dict) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


@dataclass(frozen=True)
class SealReceipt:
    race_id: str
    model_key: str
    payload_sha256: str
    sealed_at: str
    scheduled_start: Optional[str]
    pre_off: bool


class SealCollisionError(ValueError):
    pass


class SealStore:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sealed_forecasts(
              race_id TEXT NOT NULL,
              model_key TEXT NOT NULL,
              payload BLOB NOT NULL,
              payload_sha256 TEXT NOT NULL,
              sealed_at TEXT NOT NULL,
              scheduled_start TEXT,
              PRIMARY KEY(race_id, model_key)
            );
            CREATE TRIGGER IF NOT EXISTS sealed_no_update
              BEFORE UPDATE ON sealed_forecasts
              BEGIN SELECT RAISE(ABORT,'sealed forecasts are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS sealed_no_delete
              BEFORE DELETE ON sealed_forecasts
              BEGIN SELECT RAISE(ABORT,'sealed forecasts are immutable'); END;
            """
        )

    def close(self) -> None:
        self.db.close()

    def seal(
        self,
        race_id: str,
        model_key: str,
        payload: dict,
        scheduled_start: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> SealReceipt:
        sealed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        digest = payload_hash(payload)
        start_iso = (
            scheduled_start.astimezone(timezone.utc).isoformat()
            if scheduled_start else None
        )
        existing = self.db.execute(
            "SELECT payload_sha256, sealed_at, scheduled_start FROM sealed_forecasts "
            "WHERE race_id=? AND model_key=?",
            (race_id, model_key),
        ).fetchone()
        if existing:
            if existing[0] != digest:
                raise SealCollisionError(
                    f"{race_id}: different payload already sealed under {model_key}"
                )
            return SealReceipt(
                race_id, model_key, existing[0], existing[1], existing[2],
                bool(existing[2] and existing[1] < existing[2]),
            )
        with self.db:
            self.db.execute(
                "INSERT INTO sealed_forecasts VALUES(?,?,?,?,?,?)",
                (race_id, model_key, canonical(payload), digest,
                 sealed_at.isoformat(), start_iso),
            )
        return SealReceipt(
            race_id, model_key, digest, sealed_at.isoformat(), start_iso,
            bool(scheduled_start and sealed_at < scheduled_start),
        )

    def read(self, race_id: str, model_key: str) -> dict:
        row = self.db.execute(
            "SELECT payload, payload_sha256, sealed_at, scheduled_start "
            "FROM sealed_forecasts WHERE race_id=? AND model_key=?",
            (race_id, model_key),
        ).fetchone()
        if not row:
            raise KeyError(race_id)
        payload = json.loads(row[0])
        if payload_hash(payload) != row[1]:
            raise ValueError(f"{race_id}: sealed payload hash mismatch")
        return {
            "race_id": race_id, "model_key": model_key, "payload": payload,
            "receipt": {
                "payload_sha256": row[1], "sealed_at": row[2],
                "scheduled_start": row[3],
                "pre_off": bool(row[3] and row[2] < row[3]),
            },
        }

    def list(self) -> list[dict]:
        return [
            self.read(race_id, model_key)
            for race_id, model_key in self.db.execute(
                "SELECT race_id, model_key FROM sealed_forecasts ORDER BY race_id"
            ).fetchall()
        ]
