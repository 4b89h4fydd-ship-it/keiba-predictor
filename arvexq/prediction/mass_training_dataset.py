from __future__ import annotations

from typing import Any, Iterable

DATASET_VERSION = "arvexq-mass-training-dataset-v1"


def _finish_map(result: dict[str, Any]) -> dict[int, int]:
    finishers = result.get("finishers") or result.get("results") or []
    out: dict[int, int] = {}
    for row in finishers:
        if not isinstance(row, dict):
            continue
        try:
            no = int(row.get("horseNumber") or row.get("number") or 0)
            finish = int(row.get("finish") or row.get("rank") or 0)
        except (TypeError, ValueError):
            continue
        if no > 0 and finish > 0:
            out[no] = finish
    return out


def rows_from_frozen_snapshot(snapshot: dict[str, Any], final_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Join labels only after features are already frozen.

    This function intentionally accepts a frozen feature snapshot and the final result
    as two separate objects. Training code must never rebuild features from a post-race
    race object.
    """
    if not isinstance(snapshot, dict) or not isinstance(final_result, dict):
        return []
    finishes = _finish_map(final_result)
    rows: list[dict[str, Any]] = []
    race_id = str(snapshot.get("raceId") or "")
    for horse in snapshot.get("rows") or []:
        if not isinstance(horse, dict):
            continue
        try:
            no = int(horse.get("horseNumber") or 0)
        except (TypeError, ValueError):
            continue
        finish = finishes.get(no)
        if not finish:
            continue
        rows.append(
            {
                "datasetVersion": DATASET_VERSION,
                "snapshotVersion": snapshot.get("snapshotVersion"),
                "schemaVersion": snapshot.get("schemaVersion"),
                "featureHash": snapshot.get("featureHash"),
                "raceId": race_id,
                "date": snapshot.get("date"),
                "circuit": snapshot.get("circuit"),
                "track": snapshot.get("track"),
                "raceNumber": snapshot.get("raceNumber"),
                "horseNumber": no,
                "name": horse.get("name"),
                "features": horse.get("features") or {},
                "finish": finish,
                "labelWin": int(finish == 1),
                "labelTop2": int(finish <= 2),
                "labelTop3": int(finish <= 3),
            }
        )
    return rows


def group_rows_by_race(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        race_id = str(row.get("raceId") or "")
        if race_id:
            grouped.setdefault(race_id, []).append(row)
    return grouped


def time_ordered_race_ids(rows: Iterable[dict[str, Any]]) -> list[str]:
    grouped = group_rows_by_race(rows)
    sortable: list[tuple[str, str]] = []
    for race_id, race_rows in grouped.items():
        date = min(str(row.get("date") or "") for row in race_rows)
        sortable.append((date, race_id))
    return [race_id for _, race_id in sorted(sortable)]


def split_walk_forward(rows: list[dict[str, Any]], train_ratio: float = 0.7, valid_ratio: float = 0.15) -> dict[str, list[dict[str, Any]]]:
    """Chronological race-group split; never random horse-row splitting."""
    race_ids = time_ordered_race_ids(rows)
    n = len(race_ids)
    if n == 0:
        return {"train": [], "valid": [], "test": []}
    train_end = max(1, int(n * train_ratio))
    valid_end = max(train_end, int(n * (train_ratio + valid_ratio)))
    train_ids = set(race_ids[:train_end])
    valid_ids = set(race_ids[train_end:valid_end])
    test_ids = set(race_ids[valid_end:])
    return {
        "train": [row for row in rows if str(row.get("raceId") or "") in train_ids],
        "valid": [row for row in rows if str(row.get("raceId") or "") in valid_ids],
        "test": [row for row in rows if str(row.get("raceId") or "") in test_ids],
    }
