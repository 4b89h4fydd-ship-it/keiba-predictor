from __future__ import annotations

import hashlib
import json
from typing import Any

from arvexq.prediction.mass_feature_factory import (
    FEATURE_SCHEMA_VERSION,
    build_race_feature_matrix,
    feature_schema_summary,
)
from arvexq.prediction.mass_feature_selection import (
    SELECTION_VERSION,
    prune_matrix_for_snapshot,
)

SNAPSHOT_VERSION = "arvexq-mass-feature-snapshot-v2"


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_mass_feature_snapshot(detail: dict[str, Any]) -> dict[str, Any]:
    """Freeze a leakage-safe, structurally pruned pre-race feature snapshot."""
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    raw_matrix = build_race_feature_matrix(horses, detail)
    raw_summary = feature_schema_summary(raw_matrix)
    matrix = prune_matrix_for_snapshot(raw_matrix)
    rows = []
    for row in matrix:
        horse = row.get("horse") or {}
        features = row.get("features") or {}
        rows.append(
            {
                "horseNumber": int(horse.get("horseNumber") or 0),
                "name": str(horse.get("name") or ""),
                "featureCount": len(features),
                "features": dict(sorted(features.items())),
            }
        )
    summary = feature_schema_summary(matrix)
    core = {
        "snapshotVersion": SNAPSHOT_VERSION,
        "schemaVersion": FEATURE_SCHEMA_VERSION,
        "selectionVersion": SELECTION_VERSION,
        "raceId": str(detail.get("id") or detail.get("raceId") or ""),
        "date": str(detail.get("date") or ""),
        "circuit": str(detail.get("circuit") or ""),
        "track": str(detail.get("track") or ""),
        "raceNumber": int(detail.get("raceNumber") or 0),
        "distance": detail.get("distance"),
        "surface": detail.get("surface"),
        "condition": detail.get("condition", detail.get("going")),
        "horseCount": len(rows),
        "rawCandidateFeatureCount": int(raw_summary.get("featureCount") or 0),
        "featureSchema": {k: v for k, v in summary.items() if k != "featureNames"},
        "rows": rows,
    }
    core["featureHash"] = _stable_hash(core)
    return core


def attach_mass_feature_snapshot(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return detail
    snapshot = build_mass_feature_snapshot(detail)
    detail["massFeatureSnapshot"] = snapshot
    detail["massFeatureSchemaVersion"] = FEATURE_SCHEMA_VERSION
    detail["massFeatureSnapshotVersion"] = SNAPSHOT_VERSION
    detail["massFeatureHash"] = snapshot["featureHash"]
    return detail
