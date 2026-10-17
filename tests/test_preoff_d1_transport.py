from datetime import datetime, timezone, timedelta
from io import BytesIO
import json

import pytest

from arvexq.forecast.preoff_capture import capture_preoff_features
from arvexq.forecast.preoff_evidence_store import append_capture, open_store
from arvexq.forecast.preoff_d1_transport import prepare_payload, upload_capture

JST = timezone(timedelta(hours=9))
TOKEN = "test-only-research-secret-more-than-24-characters"


def fixture(tmp_path):
    detail = {"id": "jra-2026-08-01-東京-01", "date": "2026-08-01",
              "startTime": "12:00", "circuit": "中央", "track": "東京",
              "surface": "芝", "condition": "良", "distance": 1600,
              "horses": [
                  {"horseNumber": n, "age": 3, "carriedWeight": 55.0,
                   "recentRaces": [{"date": "2026-07-12", "finish": n,
                                    "fieldSize": 10, "distance": 1600,
                                    "track": "東京", "surface": "芝"}]}
                  for n in (1, 2, 3, 4)
              ]}
    snap, rec = capture_preoff_features(detail, [1, 2, 3, 4],
                                         now=datetime(2026, 8, 1, 11, 30, tzinfo=JST))
    conn = open_store(tmp_path / "capture.sqlite")
    cid = append_capture(conn, snap, rec, clock=rec["capturedAtEpoch"] + 5)
    return conn, cid, rec


class FakeResponse:
    def __init__(self, body, status=201):
        self.status, self.body = status, json.dumps(body).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, amount):
        return self.body[:amount]


def test_python_json_canonical_payload_and_transport_round_trip(monkeypatch, tmp_path):
    conn, cid, rec = fixture(tmp_path)
    monkeypatch.setenv("ARVEXQ_ENABLE_PREOFF_D1_CAPTURE", "1")
    observed = {}
    def transport(req, timeout):
        assert timeout == 12
        assert req.get_header("Authorization") == "Bearer " + TOKEN
        payload = json.loads(req.data.decode())
        observed.update(payload)
        assert "55.0" in payload["snapshotCoreCanonical"]
        assert "result::" not in payload["snapshotCoreCanonical"]
        return FakeResponse({"ok": True, "captureId": cid, "researchOnly": True})
    try:
        result = upload_capture(conn, cid, token=TOKEN,
                                clock=rec["capturedAtEpoch"] + 10, transport=transport)
        assert result["remoteAccepted"] is True
        assert observed["snapshot"]["featureHash"] == rec["featureHash"]
    finally:
        conn.close()


def test_does_not_transmit_without_opt_in_or_after_deadline(monkeypatch, tmp_path):
    conn, cid, rec = fixture(tmp_path)
    sent = []
    def transport(req, timeout):
        sent.append(True)
        return FakeResponse({"ok": True, "captureId": cid, "researchOnly": True})
    try:
        monkeypatch.delenv("ARVEXQ_ENABLE_PREOFF_D1_CAPTURE", raising=False)
        with pytest.raises(ValueError, match="disabled"):
            upload_capture(conn, cid, token=TOKEN, transport=transport)
        monkeypatch.setenv("ARVEXQ_ENABLE_PREOFF_D1_CAPTURE", "1")
        with pytest.raises(ValueError, match="post-off"):
            upload_capture(conn, cid, token=TOKEN, clock=rec["postAtEpoch"],
                           transport=transport)
        with pytest.raises(ValueError, match="stale"):
            upload_capture(conn, cid, token=TOKEN, clock=rec["capturedAtEpoch"] + 301,
                           transport=transport)
        with pytest.raises(ValueError, match="token"):
            upload_capture(conn, cid, token="bad", clock=rec["capturedAtEpoch"],
                           transport=transport)
        assert not sent
    finally:
        conn.close()


def test_rejects_acknowledgement_mismatch(monkeypatch, tmp_path):
    conn, cid, rec = fixture(tmp_path)
    monkeypatch.setenv("ARVEXQ_ENABLE_PREOFF_D1_CAPTURE", "1")
    try:
        with pytest.raises(ValueError, match="acknowledgement"):
            upload_capture(conn, cid, token=TOKEN, clock=rec["capturedAtEpoch"] + 10,
                           transport=lambda req, timeout: FakeResponse({
                               "ok": True, "captureId": "other", "researchOnly": True
                           }))
    finally:
        conn.close()
