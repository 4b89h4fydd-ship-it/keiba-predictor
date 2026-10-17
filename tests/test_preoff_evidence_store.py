"""Immutable research evidence store regressions; no production writes."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import sqlite3

import pytest

from arvexq.forecast.preoff_capture import capture_preoff_features
from arvexq.forecast.preoff_evidence_store import (
    append_capture, read_capture, open_store,
)

JST = timezone(timedelta(hours=9))


def evidence():
    detail = {
        "id": "jra-2026-08-01-東京-01", "date": "2026-08-01",
        "startTime": "12:00", "circuit": "中央", "track": "東京",
        "surface": "芝", "distance": 1600, "condition": "良",
        "horses": [
            {"horseNumber": n, "age": 3, "carriedWeight": 55,
             "recentRaces": [
                 {"date": "2026-07-20", "finish": n, "fieldSize": 10,
                  "track": "東京", "surface": "芝", "distance": 1600}
             ]} for n in range(1, 5)
        ],
    }
    return capture_preoff_features(
        detail, [1, 2, 3, 4],
        now=datetime(2026, 8, 1, 11, 30, tzinfo=JST),
    )


def test_persist_read_and_repeat_are_byte_identical(tmp_path):
    snapshot, receipt = evidence()
    original = deepcopy(snapshot), deepcopy(receipt)
    clock = receipt["capturedAtEpoch"] + 5
    with open_store(tmp_path / "new-preoff.sqlite") as conn:
        cid = append_capture(conn, snapshot, receipt, clock=clock)
        assert cid == append_capture(conn, snapshot, receipt, clock=clock + 2)
        record = read_capture(conn, cid)
        assert record["snapshot"] == snapshot
        assert record["receipt"] == receipt
        assert record["storedAtEpoch"] == clock
        assert conn.execute("SELECT count(*) FROM forecast_preoff_evidence").fetchone()[0] == 1
        assert (snapshot, receipt) == original
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM forecast_preoff_evidence")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE forecast_preoff_evidence SET race_id='altered'")
        conn.rollback()


def test_rejects_late_post_off_and_unverified_receipts(tmp_path):
    snapshot, receipt = evidence()
    with open_store(tmp_path / "new-preoff.sqlite") as conn:
        with pytest.raises(ValueError, match="promptly"):
            append_capture(conn, snapshot, receipt, clock=receipt["postAtEpoch"])
        with pytest.raises(ValueError, match="promptly"):
            append_capture(conn, snapshot, receipt, clock=receipt["capturedAtEpoch"] + 1000)
        tampered = deepcopy(snapshot)
        tampered["rows"][0]["features"]["static::age"] = 999
        with pytest.raises(ValueError, match="hash"):
            append_capture(conn, tampered, receipt, clock=receipt["capturedAtEpoch"])
        forged = dict(receipt, capturedAtEpoch=receipt["capturedAtEpoch"] + 1)
        with pytest.raises(ValueError, match="digest"):
            append_capture(conn, snapshot, forged, clock=receipt["capturedAtEpoch"] + 2)
        assert conn.execute("SELECT count(*) FROM forecast_preoff_evidence").fetchone()[0] == 0


def test_storage_detects_out_of_band_tampering(tmp_path):
    snapshot, receipt = evidence()
    with open_store(tmp_path / "new-preoff.sqlite") as conn:
        cid = append_capture(conn, snapshot, receipt, clock=receipt["capturedAtEpoch"])
        conn.execute("DROP TRIGGER prevent_forecast_evidence_update")
        conn.execute("UPDATE forecast_preoff_evidence SET stored_at_epoch=0")
        conn.commit()
        with pytest.raises(ValueError, match="metadata mismatch"):
            read_capture(conn, cid)


def test_cannot_use_backfilled_historical_data_as_live_capture(tmp_path):
    snapshot, receipt = evidence()
    with open_store(tmp_path / "new-preoff.sqlite") as conn:
        with pytest.raises(ValueError, match="promptly"):
            append_capture(conn, snapshot, receipt)
