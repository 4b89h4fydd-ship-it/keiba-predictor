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
    result = audit_days(days=7, per_circuit=2, end_date="2026-10-18")
    assert result["start"] == "2026-10-12"
    assert result["end"] == "2026-10-18"
    assert result["circuits"]["jra"]["checked"] == 6
    assert result["circuits"]["nar"]["checked"] == 14
    assert result["circuits"]["jra"]["verified"] == 6
    assert result["circuits"]["nar"]["verified"] == 14
    assert result["allSampledVerified"] is True
    assert result["fullArchiveVerified"] is False
    assert result["liveApi429Resolved"] is False


def test_actual_stage64_nar_gap_archive_vs_saved_snapshot():
    """Only compare immutable repository evidence; this is NOT a live D1 read."""
    from collections import Counter
    from pathlib import Path

    base = Path(__file__).resolve().parents[1]
    day = "2026-10-16"
    folder = base / "arvexq/ui/static/saved-snapshots"
    manifest = json.loads((folder / (day + ".json")).read_text(encoding="utf-8"))
    cards = json.loads(
        (base / "arvexq/ui/static/racecards" / (day + ".json")).read_text(
            encoding="utf-8"))
    archive = json.loads(
        (base / "docs/research/stage64-results/official_gap_recheck.json")
        .read_text(encoding="utf-8"))
    observations = archive["observations"]
    by_race = {race["id"]: race for race in cards["races"]}
    target_ids = {row["raceId"] for row in observations}
    assert len(target_ids) == archive["targetRaces"] == 11
    assert len(observations) == archive["targetHorses"] == 34
    assert all(rid.startswith("nar-") for rid in target_ids)

    restored = {}
    for rid in target_ids:
        entry = manifest["races"][rid]
        envelope = json.loads(
            (folder / entry["file"]).read_text(encoding="utf-8"))
        # The existing bounded decoder checks SHA-256 and decompressed length.
        saved = _restore(envelope, entry)
        assert saved["id"] == rid
        assert saved["date"] == day and saved["circuit"] == "地方"
        restored[rid] = saved

    direct_count = Counter()
    observed_saved = []
    for row in observations:
        rid, no, name = row["raceId"], row["horseNumber"], row["name"]
        stored_horses = {h["horseNumber"]: h
                         for h in restored[rid]["horses"]}
        official_card_horses = {h["horseNumber"]: h
                                for h in by_race[rid]["horses"]}
        assert no in stored_horses and no in official_card_horses
        assert stored_horses[no]["name"] == name
        assert official_card_horses[no]["name"] == name
        horse = stored_horses[no]
        saved_recent = horse.get("recentRaces") or []
        saved_all = horse.get("allPastRuns") or []
        direct_count[(len(saved_recent), len(saved_all))] += 1
        if saved_recent or saved_all:
            observed_saved.append((rid, no, name, len(saved_recent), len(saved_all)))
    # The Stage64 official-source gap is NOT equivalent to an absent
    # saved history: one race retained three prior runs by another path.
    assert direct_count == {(0, 0): 33, (3, 3): 1}
    assert observed_saved == [
        ("nar-2026-10-16-川崎-03", 2, "アークブレイブ", 3, 3)
    ]
