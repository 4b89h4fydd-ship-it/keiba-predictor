"""Non-destructive storage of observed NAR official race metadata.

The existing CSV ingestion path must call these helpers after parsing.
Do not infer unavailable values or overwrite previously observed metadata.
"""
from __future__ import annotations

from collections.abc import Mapping
import sqlite3

COLUMNS = ("surface", "direction", "class_condition")


def official_race_metadata(row: list[str], indexes: Mapping[str, int]) -> dict[str, str]:
    """Return factual CSV values; absent columns remain empty."""
    values: dict[str, str] = {}
    for field in COLUMNS:
        position = indexes.get(field)
        values[field] = (str(row[position]).strip().replace("\u3000", " ")
                         if isinstance(position, int) and 0 <= position < len(row)
                         else "")
    return values


def migrate_race_metadata(conn: sqlite3.Connection) -> None:
    """Add missing columns to an existing races table without replacing rows."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(races)")}
    for field in COLUMNS:
        if field not in existing:
            conn.execute(
                f"ALTER TABLE races ADD COLUMN {field} TEXT NOT NULL DEFAULT ''"
            )


def update_race_metadata(conn: sqlite3.Connection, identity: tuple[str, str, int],
                         metadata: Mapping[str, str]) -> bool:
    """Update only known values for an existing official race."""
    provided = {key: str(metadata[key]).strip()
                for key in COLUMNS if metadata.get(key) not in (None, "", "不明")}
    if not provided:
        return False
    assignments = ", ".join(f"{key}=?" for key in provided)
    cursor = conn.execute(
        f"UPDATE races SET {assignments} WHERE track=? AND date=? AND race_no=?",
        (*provided.values(), *identity),
    )
    return cursor.rowcount > 0


def audit_official_race_metadata(rows: list[list[str]],
                                 indexes: Mapping[str, int]) -> dict:
    """Count observed metadata coverage without changing input rows."""
    counts = {key: 0 for key in COLUMNS}
    missing = {key: 0 for key in COLUMNS}
    total = 0
    for row in rows:
        if not isinstance(row, list):
            continue
        total += 1
        fields = official_race_metadata(row, indexes)
        for key in COLUMNS:
            if fields[key] and fields[key] != "不明":
                counts[key] += 1
            else:
                missing[key] += 1
    return {"raceRows": total, "observed": counts, "missing": missing,
            "coveragePercent": {
                key: round(counts[key] * 100 / total, 2) if total else None
                for key in COLUMNS
            }}
