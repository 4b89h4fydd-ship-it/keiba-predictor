"""Append-only local SQLite storage for independently captured pre-off evidence.

NOT a D1 connector, proof of trustworthy clock, or production predictor.
A storage service must use a trusted clock and a protected DB path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
from pathlib import Path

from .frozen_research_input import from_frozen_snapshot

STORE_VERSION = "arvexq-preoff-receipt-store-v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def init_store(connection):
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS forecast_preoff_evidence (
        capture_id TEXT PRIMARY KEY,
        race_id TEXT NOT NULL,
        feature_hash TEXT NOT NULL,
        receipt_hash TEXT NOT NULL,
        snapshot_json TEXT NOT NULL,
        receipt_json TEXT NOT NULL,
        captured_at_epoch INTEGER NOT NULL,
        stored_at_epoch INTEGER NOT NULL,
        post_at_epoch INTEGER NOT NULL,
        UNIQUE(race_id, feature_hash, captured_at_epoch)
    );
    CREATE TRIGGER IF NOT EXISTS prevent_forecast_evidence_update
    BEFORE UPDATE ON forecast_preoff_evidence
    BEGIN SELECT RAISE(ABORT, 'append-only evidence cannot be updated'); END;
    CREATE TRIGGER IF NOT EXISTS prevent_forecast_evidence_delete
    BEFORE DELETE ON forecast_preoff_evidence
    BEGIN SELECT RAISE(ABORT, 'append-only evidence cannot be deleted'); END;
    """)


def _validate(snapshot, receipt):
    # An attestation field is NOT a trusted signature. Store only when a
    # separately privileged collector attests capture time and runner roster.
    from_frozen_snapshot(snapshot, receipt)
    provided = receipt.get("receiptHash")
    core = {k: v for k, v in receipt.items() if k != "receiptHash"}
    if not isinstance(provided, str) or provided != digest(core):
        raise ValueError("capture receipt digest mismatch")
    if receipt.get("version") != "arvexq-preoff-raw-evidence-v1":
        raise ValueError("unsupported capture receipt version")


def append_capture(connection, snapshot, receipt, *, clock=None, max_delay_seconds=300):
    """Persist atomic evidence at acquisition; no post-off or late imports.

    A caller-provided clock exists only for deterministic tests. Production
    callers must omit clock and use the local trusted host time. SQLite itself
    is not a secure time authority; host protection remains essential.
    """
    _validate(snapshot, receipt)
    if clock is None:
        now = int(datetime.now(timezone.utc).timestamp())
    elif type(clock) is int:
        now = clock
    else:
        raise ValueError("test clock must be an integer Unix timestamp")
    captured = receipt["capturedAtEpoch"]
    post = receipt["postAtEpoch"]
    if not (captured <= now < post and 0 <= now - captured <= max_delay_seconds):
        raise ValueError("capture must be promptly stored before scheduled post")
    capture_id = digest({"raceId": receipt["raceId"],
                         "featureHash": receipt["featureHash"],
                         "capturedAtEpoch": captured})
    init_store(connection)
    fields = (capture_id, receipt["raceId"], receipt["featureHash"], receipt["receiptHash"],
              canonical(snapshot).decode(), canonical(receipt).decode(), captured, now, post)
    try:
        with connection:
            connection.execute("""
                INSERT INTO forecast_preoff_evidence
                  (capture_id, race_id, feature_hash, receipt_hash, snapshot_json,
                   receipt_json, captured_at_epoch, stored_at_epoch, post_at_epoch)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, fields)
    except sqlite3.IntegrityError:
        # Immutable replay is idempotent; a conflict with different bytes fails.
        existing = connection.execute(
            "SELECT snapshot_json, receipt_json FROM forecast_preoff_evidence WHERE capture_id=?",
            (capture_id,)).fetchone()
        if existing is None or existing != (fields[4], fields[5]):
            raise ValueError("capture identity collision with different evidence") from None
    return capture_id


def read_capture(connection, capture_id):
    row = connection.execute("""
        SELECT race_id, feature_hash, receipt_hash, snapshot_json, receipt_json,
               captured_at_epoch, stored_at_epoch, post_at_epoch
        FROM forecast_preoff_evidence WHERE capture_id=?
    """, (capture_id,)).fetchone()
    if row is None:
        raise KeyError("unknown capture")
    rid, feature_hash, receipt_hash, snapshot_json, receipt_json, captured, stored, post = row
    snapshot, receipt = json.loads(snapshot_json), json.loads(receipt_json)
    _validate(snapshot, receipt)
    if (receipt["raceId"] != rid or receipt["featureHash"] != feature_hash
            or receipt["receiptHash"] != receipt_hash
            or receipt["capturedAtEpoch"] != captured or receipt["postAtEpoch"] != post
            or not captured <= stored < post):
        raise ValueError("stored evidence metadata mismatch")
    expected = digest({"raceId": rid, "featureHash": feature_hash,
                       "capturedAtEpoch": captured})
    if expected != capture_id:
        raise ValueError("capture ID mismatch")
    return {"captureId": capture_id, "snapshot": snapshot, "receipt": receipt,
            "storedAtEpoch": stored, "storeVersion": STORE_VERSION}


def open_store(path):
    """Local-only connection. Do not treat this as a Cloudflare D1 connection."""
    connection = sqlite3.connect(str(Path(path)), timeout=10)
    init_store(connection)
    return connection
