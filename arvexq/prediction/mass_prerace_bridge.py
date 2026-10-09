from __future__ import annotations

from typing import Any

from arvexq.prediction.mass_feature_snapshot import (
    SNAPSHOT_VERSION,
    build_mass_feature_snapshot,
)
from arvexq.prediction.mass_feature_factory import FEATURE_SCHEMA_VERSION
from arvexq.prediction.mass_feature_transport import restore_snapshot

FROZEN_MASS_KEYS = (
    "massFeatureSnapshot",
    "massFeatureArchive",
    "massFeatureSchemaVersion",
    "massFeatureSnapshotVersion",
    "massFeatureHash",
)


def frozen_mass_fields(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {}
    out = {key: detail.get(key) for key in FROZEN_MASS_KEYS if detail.get(key) is not None}
    snapshot = out.get("massFeatureSnapshot")
    if isinstance(snapshot, dict) and snapshot.get("featureHash"):
        out.setdefault("massFeatureHash", snapshot.get("featureHash"))
        out.setdefault("massFeatureSchemaVersion", snapshot.get("schemaVersion") or FEATURE_SCHEMA_VERSION)
        out.setdefault("massFeatureSnapshotVersion", snapshot.get("snapshotVersion") or SNAPSHOT_VERSION)
    archive = out.get("massFeatureArchive")
    if isinstance(archive, dict):
        out.setdefault("massFeatureHash", archive.get("featureHash"))
        out.setdefault("massFeatureSchemaVersion", FEATURE_SCHEMA_VERSION)
        out.setdefault("massFeatureSnapshotVersion", SNAPSHOT_VERSION)
    return out


def prepare_mass_prerace_fields(detail: dict[str, Any]) -> dict[str, Any]:
    """Build the expensive mass-feature snapshot only when a pre-race lock exists.

    Existing frozen fields win. This makes repeated persistence cheap and immutable.
    """
    if not isinstance(detail, dict):
        return {}
    lock = detail.get("preRacePrediction")
    if not isinstance(lock, dict):
        return {}
    existing = frozen_mass_fields(detail)
    if isinstance(existing.get("massFeatureSnapshot"), dict) and existing.get("massFeatureHash"):
        return existing
    archive = existing.get("massFeatureArchive")
    if isinstance(archive, dict):
        snapshot = restore_snapshot(archive,
                                    race_id=str(detail.get("id") or detail.get("raceId") or ""),
                                    race_date=str(detail.get("date") or ""))
        if snapshot.get("featureHash") != existing.get("massFeatureHash"):
            raise ValueError("frozen mass feature archive is not the pre-race evidence")
        return existing
    snapshot = build_mass_feature_snapshot(detail)
    return {
        "massFeatureSnapshot": snapshot,
        "massFeatureSchemaVersion": FEATURE_SCHEMA_VERSION,
        "massFeatureSnapshotVersion": SNAPSHOT_VERSION,
        "massFeatureHash": snapshot.get("featureHash"),
    }


def apply_mass_prerace_fields(detail: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    """Attach frozen fields and a small pointer into the existing pre-race lock."""
    if not isinstance(detail, dict) or not isinstance(fields, dict) or not fields:
        return detail
    for key in FROZEN_MASS_KEYS:
        if key in fields:
            detail[key] = fields[key]
    lock = detail.get("preRacePrediction")
    if isinstance(lock, dict):
        lock = dict(lock)
        lock["massFeatureHash"] = detail.get("massFeatureHash")
        lock["massFeatureSchemaVersion"] = detail.get("massFeatureSchemaVersion")
        lock["massFeatureSnapshotVersion"] = detail.get("massFeatureSnapshotVersion")
        detail["preRacePrediction"] = lock
    return detail
