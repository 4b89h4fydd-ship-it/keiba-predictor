from __future__ import annotations

import hashlib
import json
from typing import Any

from arvexq.selection.race_selectability import MODEL_VERSION, build_race_selectability_features

SNAPSHOT_VERSION = "arvexq-race-selectability-snapshot-v1"
FROZEN_KEYS = (
    "raceSelectabilitySnapshot",
    "raceSelectabilitySnapshotVersion",
    "raceSelectabilityModelVersion",
    "raceSelectabilityHash",
)


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_race_selectability_snapshot(detail: dict[str, Any]) -> dict[str, Any]:
    features = build_race_selectability_features(detail)
    payload = {
        "snapshotVersion": SNAPSHOT_VERSION,
        "modelVersion": MODEL_VERSION,
        "raceId": detail.get("id") or detail.get("raceId"),
        "date": detail.get("date"),
        "circuit": detail.get("circuit"),
        "track": detail.get("track"),
        "raceNumber": detail.get("raceNumber"),
        "features": features,
    }
    payload["featureHash"] = _hash_payload(payload)
    return payload


def frozen_selectability_fields(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {}
    out = {key: detail.get(key) for key in FROZEN_KEYS if detail.get(key) is not None}
    snap = out.get("raceSelectabilitySnapshot")
    if isinstance(snap, dict):
        out.setdefault("raceSelectabilityHash", snap.get("featureHash"))
        out.setdefault("raceSelectabilitySnapshotVersion", snap.get("snapshotVersion") or SNAPSHOT_VERSION)
        out.setdefault("raceSelectabilityModelVersion", snap.get("modelVersion") or MODEL_VERSION)
    return out


def prepare_race_selectability_fields(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict) or not isinstance(detail.get("preRacePrediction"), dict):
        return {}
    existing = frozen_selectability_fields(detail)
    if isinstance(existing.get("raceSelectabilitySnapshot"), dict) and existing.get("raceSelectabilityHash"):
        return existing
    snapshot = build_race_selectability_snapshot(detail)
    return {
        "raceSelectabilitySnapshot": snapshot,
        "raceSelectabilitySnapshotVersion": SNAPSHOT_VERSION,
        "raceSelectabilityModelVersion": MODEL_VERSION,
        "raceSelectabilityHash": snapshot.get("featureHash"),
    }


def apply_race_selectability_fields(detail: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict) or not isinstance(fields, dict) or not fields:
        return detail
    for key in FROZEN_KEYS:
        if key in fields:
            detail[key] = fields[key]
    lock = detail.get("preRacePrediction")
    if isinstance(lock, dict):
        lock = dict(lock)
        lock["raceSelectabilityHash"] = detail.get("raceSelectabilityHash")
        lock["raceSelectabilitySnapshotVersion"] = detail.get("raceSelectabilitySnapshotVersion")
        lock["raceSelectabilityModelVersion"] = detail.get("raceSelectabilityModelVersion")
        detail["preRacePrediction"] = lock
    return detail
