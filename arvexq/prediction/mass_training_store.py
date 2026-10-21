from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from arvexq.prediction.mass_training_dataset import rows_from_frozen_snapshot
from arvexq.prediction.mass_feature_transport import recover_mass_detail, _feature_hash

STORE_VERSION = "arvexq-mass-training-store-v1"


def _confirmed_result(detail: dict[str, Any]) -> dict[str, Any] | None:
    result = detail.get("result")
    if not isinstance(result, dict):
        return None
    if str(result.get("status") or "") != "確定":
        return None
    if not (result.get("finishers") or result.get("results")):
        return None
    return result


def frozen_training_rows_from_detail(detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Use only the already-frozen feature snapshot; never rebuild from final detail."""
    if not isinstance(detail, dict):
        return []
    result = _confirmed_result(detail)
    if result is None:
        return []
    # Read the frozen pre-race evidence from its authenticated lossless
    # archive. Never infer feature rows from the already-known finishers.
    if not isinstance(detail.get("massFeatureSnapshot"), dict) and detail.get("massFeatureArchive"):
        try:
            detail = recover_mass_detail(detail)
        except ValueError:
            # An existing frozen snapshot may have an invalid historical origin
            # hash. Keep it archived but do not use it to train or inflate accuracy.
            return []
    snapshot = detail.get("massFeatureSnapshot")
    if not isinstance(snapshot, dict):
        return []
    if not snapshot.get("featureHash") or not snapshot.get("rows"):
        return []
    # Both direct and compressed copies use the SAME origin-content hash.
    # A direct snapshot used to bypass this guard, while compressed snapshots
    # were verified during restore_snapshot().
    expected = str(snapshot["featureHash"])
    if expected != _feature_hash(snapshot):
        return []
    if (str(snapshot.get("raceId") or "") != str(detail.get("id") or detail.get("raceId") or "")
            or str(snapshot.get("date") or "") != str(detail.get("date") or "")):
        return []
    # Existing lossless archive details can omit the outer circuit; in that
    # legacy shape the immutable snapshot remains the owner of circuit.
    # When the outer circuit is present it must agree with the frozen owner.
    outer_circuit = detail.get("circuit")
    if outer_circuit not in (None, "") and str(snapshot.get("circuit") or "") != str(outer_circuit):
        return []
    if detail.get("massFeatureHash") and str(detail["massFeatureHash"]) != expected:
        return []
    lock = detail.get("preRacePrediction")
    if isinstance(lock, dict) and lock.get("massFeatureHash") and str(lock["massFeatureHash"]) != expected:
        return []
    archive = detail.get("massFeatureArchive")
    if isinstance(archive, dict):
        if archive.get("originHashVerified") is False or str(archive.get("featureHash") or "") != expected:
            return []
    # Explicitly provisional or disqualified captures are never promoted
    # just because their feature bytes happen to hash correctly.
    if detail.get("verifiedForTraining") is False or snapshot.get("verifiedForTraining") is False:
        return []
    return rows_from_frozen_snapshot(snapshot, result)


def iter_frozen_training_rows(
    db_path: str | Path,
    *,
    circuit: str = "",
    start_date: str = "",
    end_date: str = "",
) -> Iterable[dict[str, Any]]:
    """Read finalized RaceDataBank rows and emit only leakage-safe frozen examples."""
    path = Path(db_path)
    if not path.exists():
        return
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        where: list[str] = []
        args: list[Any] = []
        if circuit:
            where.append("circuit=?")
            args.append(circuit)
        if start_date:
            where.append("race_date>=?")
            args.append(start_date)
        if end_date:
            where.append("race_date<=?")
            args.append(end_date)
        sql = "SELECT race_id,race_date,circuit,payload FROM race_snapshots"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY race_date,race_id"
        dbrows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()

    seen_hashes: set[str] = set()
    for row in dbrows:
        try:
            detail = json.loads(row["payload"])
        except Exception:
            continue
        snapshot = detail.get("massFeatureSnapshot") if isinstance(detail, dict) else None
        archive = detail.get("massFeatureArchive") if isinstance(detail, dict) else None
        feature_hash = str((snapshot or {}).get("featureHash") or
                           (archive or {}).get("featureHash") or "")
        if not feature_hash or feature_hash in seen_hashes:
            continue
        examples = frozen_training_rows_from_detail(detail)
        if not examples:
            continue
        # The SQLite index remains a separate authority for race identity and
        # circuit. This also checks legacy payloads with no top-level circuit.
        aliases = {"中央": "jra", "jra": "jra", "地方": "nar", "nar": "nar"}
        source_circuit = aliases.get(str(row["circuit"] or ""))
        frozen_circuit = aliases.get(str(examples[0].get("circuit") or ""))
        if (str(row["race_id"]) != str(examples[0]["raceId"])
                or str(row["race_date"]) != str(examples[0]["date"])
                or source_circuit is None or source_circuit != frozen_circuit):
            continue
        seen_hashes.add(feature_hash)
        for example in examples:
            example["storeVersion"] = STORE_VERSION
            yield example


def load_frozen_training_rows(
    db_path: str | Path,
    *,
    circuit: str = "",
    start_date: str = "",
    end_date: str = "",
) -> list[dict[str, Any]]:
    return list(
        iter_frozen_training_rows(
            db_path,
            circuit=circuit,
            start_date=start_date,
            end_date=end_date,
        )
    )
