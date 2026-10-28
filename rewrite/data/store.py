"""Append-only storage for raw snapshots and normalized races.

Raw payloads are stored byte-exact with their SHA-256. The first write
of a given (kind, race key, hash) wins and is never overwritten, so a
snapshot taken before a race cannot be silently replaced afterwards.
Normalized records are stored as JSON alongside the snapshot they came
from, keeping the raw -> normalized link auditable.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .normalize import RaceRecord
from .sources import RawPayload

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_snapshots (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    race_key TEXT NOT NULL,
    source_url TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    body BLOB NOT NULL,
    UNIQUE(kind, race_key, sha256)
);
CREATE TABLE IF NOT EXISTS normalized_races (
    race_id TEXT PRIMARY KEY,
    race_date TEXT NOT NULL,
    source_url TEXT NOT NULL,
    snapshot_sha256 TEXT NOT NULL,
    normalized_json TEXT NOT NULL,
    stored_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_reports (
    id INTEGER PRIMARY KEY,
    race_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);
"""


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def save_raw(self, payload: RawPayload, race_key: str) -> tuple[str, bool]:
        """Store exact bytes. Returns (sha256, inserted?)."""
        digest = hashlib.sha256(payload.body).hexdigest()
        cursor = self.db.execute(
            "INSERT OR IGNORE INTO raw_snapshots"
            " (kind, race_key, source_url, fetched_at, sha256, body)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                payload.kind,
                race_key,
                payload.source_url,
                payload.fetched_at.isoformat(),
                digest,
                payload.body,
            ),
        )
        self.db.commit()
        return digest, cursor.rowcount == 1

    def raw_body(self, kind: str, race_key: str, sha256: str) -> Optional[bytes]:
        row = self.db.execute(
            "SELECT body FROM raw_snapshots WHERE kind=? AND race_key=? AND sha256=?",
            (kind, race_key, sha256),
        ).fetchone()
        return row[0] if row else None

    def verify_raw(self, kind: str, race_key: str, sha256: str) -> bool:
        body = self.raw_body(kind, race_key, sha256)
        return body is not None and hashlib.sha256(body).hexdigest() == sha256

    def save_normalized(self, race: RaceRecord, snapshot_sha256: str) -> None:
        payload = json.dumps(asdict(race), ensure_ascii=False, default=_json_default)
        self.db.execute(
            "INSERT OR REPLACE INTO normalized_races"
            " (race_id, race_date, source_url, snapshot_sha256, normalized_json, stored_at)"
            " VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (race.race_id, race.date, race.source, snapshot_sha256, payload),
        )
        self.db.commit()

    def save_quality(self, race_date: str, report: dict) -> None:
        self.db.execute(
            "INSERT INTO quality_reports (race_date, created_at, report_json)"
            " VALUES (?, datetime('now'), ?)",
            (race_date, json.dumps(report, ensure_ascii=False, default=_json_default)),
        )
        self.db.commit()

    def load_races(self) -> list[RaceRecord]:
        """Rebuild normalized dataclasses from their stored JSON form."""
        from .normalize import Obs, PastRun, RaceRecord, RunnerRecord
        from ..safety.contracts import Segment

        def _obs(d: dict) -> Obs:
            return Obs(d.get("value"), d.get("source", ""), d.get("missing_reason"))

        def _past(d: dict) -> PastRun:
            kwargs = {
                name: _obs(d[name])
                for name in (
                    "track", "distance", "surface", "finish", "field_size",
                    "margin_text", "time_seconds", "jockey", "condition",
                    "weather", "time_behind_winner", "margin_seconds",
                    "carried_weight", "race_title",
                )
                if isinstance(d.get(name), dict)
            }
            return PastRun(
                date=d.get("date", ""),
                corner_positions=tuple(d.get("corner_positions") or ()),
                **kwargs,
            )

        def _runner(d: dict) -> RunnerRecord:
            return RunnerRecord(
                number=d["number"],
                horse_id=_obs(d["horse_id"]),
                name=_obs(d["name"]),
                frame_number=_obs(d["frame_number"]),
                age=_obs(d["age"]),
                sex=_obs(d["sex"]),
                jockey=_obs(d["jockey"]),
                trainer=_obs(d["trainer"]),
                carried_weight=_obs(d["carried_weight"]),
                body_weight=_obs(d["body_weight"]),
                body_weight_change=_obs(d["body_weight_change"]),
                win_odds=_obs(d["win_odds"]),
                scratched=bool(d["scratched"]),
                past_runs=tuple(_past(p) for p in d.get("past_runs") or ()),
                rejected_future_runs=d.get("rejected_future_runs", 0),
            )

        races: list[RaceRecord] = []
        for (payload,) in self.db.execute(
            "SELECT normalized_json FROM normalized_races ORDER BY race_id"
        ):
            d = json.loads(payload)
            races.append(
                RaceRecord(
                    race_id=d["race_id"],
                    date=d["date"],
                    circuit=_obs(d["circuit"]),
                    track=d["track"],
                    race_number=_obs(d["race_number"]),
                    title=_obs(d["title"]),
                    start_time=_obs(d["start_time"]),
                    distance=_obs(d["distance"]),
                    surface=_obs(d["surface"]),
                    weather=_obs(d["weather"]),
                    condition=_obs(d["condition"]),
                    updated_at=_obs(d["updated_at"]),
                    segment=Segment(d["segment"]),
                    source=d["source"],
                    runners=tuple(_runner(r) for r in d.get("runners") or ()),
                )
            )
        return races

    def counts(self) -> dict[str, int]:
        out = {}
        for table in ("raw_snapshots", "normalized_races", "quality_reports"):
            out[table] = self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        return out
