"""Bounded offline checksum and identity checks; no production requests."""
from __future__ import annotations

import base64
from copy import deepcopy
import gzip
import hashlib
import json

import pytest

from arvexq.v3.audit.snapshot_digest import (
    _restore, verify_one, select_samples, audit_saved_blobs
)
from scripts.arvexq_v3_blob_digest_audit import audit_days


def build(tmp_path, *, circuit="nar"):
    date = "2026-10-18"
    track = "高知" if circuit == "nar" else "京都"
    rid = f"{circuit}-{date}-{track}-01"
    horse = {"horseNumber": 1, "name": "テスト馬"}
    race = {"id": rid, "date": date, "circuit": "地方" if circuit == "nar" else "中央",
            "horses": [horse], "preRaceBet": {"do-not-publish": "sealing"}}
    raw = json.dumps(race, ensure_ascii=False, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()
    ref = {"sha256": sha, "file": sha + ".json", "bytes": len(raw), "horses": 1}
    payload = {"version": "arvexq-saved-snapshot-v1", "sha256": sha, "bytes": len(raw),
               "gzipBase64": base64.b64encode(gzip.compress(raw, mtime=0)).decode()}
    folder = tmp_path / "saved-snapshots"
    folder.mkdir(exist_ok=True)
    (folder / ref["file"]).write_text(json.dumps(payload), encoding="utf-8")
    cards = {"date": date, "races": [{"id": rid, "circuit": race["circuit"],
                                     "horses": [horse]}]}
    manifest = {"date": date, "races": {rid: ref}}
    return rid, ref, payload, cards, manifest


def test_valid_sha256_and_runner_identity(tmp_path):
    rid, ref, payload, cards, manifest = build(tmp_path)
    copy = deepcopy(payload)
    x = verify_one(tmp_path / "saved-snapshots", rid, ref, day=cards["date"],
                   circuit="nar", card_horses=cards["races"][0]["horses"])
    assert x["status"] == "verified" and x["sha256"] == ref["sha256"]
    assert payload == copy
    assert audit_saved_blobs(tmp_path, cards, manifest)["allSampledVerified"]
    assert not audit_saved_blobs(tmp_path, cards, manifest)["fullArchiveVerified"]


def test_digest_corruption_and_manifest_changes_fail(tmp_path):
    _, ref, payload, cards, manifest = build(tmp_path)
    bad = deepcopy(payload)
    bad["bytes"] += 1
    with pytest.raises(ValueError, match="envelope-mismatch"):
        _restore(bad, ref)
    bad = deepcopy(payload)
    bad["gzipBase64"] = "not-valid-base64!"
    with pytest.raises(ValueError, match="base64-invalid"):
        _restore(bad, ref)
    bad = deepcopy(payload)
    bad["gzipBase64"] = base64.b64encode(gzip.compress(b"wrong", mtime=0)).decode()
    with pytest.raises(ValueError, match="sha256-or-length-mismatch"):
        _restore(bad, ref)
    ref["bytes"] += 1
    with pytest.raises(ValueError, match="envelope-mismatch"):
        _restore(payload, ref)


def test_wrong_runner_and_missing_payload_fail(tmp_path):
    rid, ref, payload, cards, manifest = build(tmp_path)
    with pytest.raises(ValueError, match="identity"):
        verify_one(tmp_path / "saved-snapshots", rid, ref, day=cards["date"],
                   circuit="nar", card_horses=[{"horseNumber": 1, "name": "別の馬"}])
    (tmp_path / "saved-snapshots" / ref["file"]).unlink()
    x = audit_saved_blobs(tmp_path, cards, manifest)
    assert x["samples"][0]["errorCode"] == "snapshot-payload-file-missing"
    assert not x["allSampledVerified"]


def test_sample_selection_and_circuit_isolation(tmp_path):
    _, _, _, cards, manifest = build(tmp_path)
    assert len(select_samples(cards, manifest)) == 1
    cards["races"][0]["circuit"] = "中央"
    with pytest.raises(ValueError, match="contradictory"):
        select_samples(cards, manifest)


def test_actual_seven_day_digest_samples_are_bounded_offline():
    result = audit_days(days=7, per_circuit=2)
    assert result["start"] == "2026-10-12"
    assert result["end"] == "2026-10-18"
    assert result["circuits"]["jra"]["checked"] == 6
    assert result["circuits"]["nar"]["checked"] == 14
    assert result["circuits"]["jra"]["verified"] == 6
    assert result["circuits"]["nar"]["verified"] == 14
    assert result["allSampledVerified"] is True
    assert result["fullArchiveVerified"] is False
    assert result["liveApi429Resolved"] is False
