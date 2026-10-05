#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sanitize restored ARVEXQ SQLite caches before runtime start.

GitHub Actions caches can preserve a SQLite file after an interrupted writer or
with stale WAL/SHM sidecars.  D1 is the serving source of truth, so a malformed
local SQLite cache must never be allowed to slow or break prefetch/live/result
jobs.  This helper removes transient sidecars, runs PRAGMA quick_check on every
SQLite database under KEIBA_DATA_DIR, and deletes only databases that fail the
check so app.py can recreate them cleanly.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"


def _unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except TypeError:  # pragma: no cover - Python <3.8 compatibility
        if path.exists():
            path.unlink()


def _sidecars(path: Path) -> list[Path]:
    return [
        Path(str(path) + "-wal"),
        Path(str(path) + "-shm"),
        Path(str(path) + "-journal"),
    ]


def _looks_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC
    except OSError:
        return False


def _quick_check(path: Path) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(str(path), timeout=2.0)
        try:
            row = conn.execute("PRAGMA quick_check").fetchone()
        finally:
            conn.close()
        value = str(row[0] if row else "").strip().lower()
        return value == "ok", value or "empty quick_check result"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def sanitize(root: Path) -> tuple[int, int, list[str]]:
    root.mkdir(parents=True, exist_ok=True)

    # WAL/SHM/journal files are process-local. Never reuse them on a new runner.
    for pattern in ("*-wal", "*-shm", "*-journal"):
        for sidecar in root.rglob(pattern):
            if sidecar.is_file():
                _unlink(sidecar)

    checked = 0
    removed: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if not _looks_sqlite(path):
            continue
        checked += 1
        ok, reason = _quick_check(path)
        if ok:
            print("SQLITE_CACHE_OK", path)
            continue
        print("SQLITE_CACHE_BAD", path, reason)
        for sidecar in _sidecars(path):
            _unlink(sidecar)
        _unlink(path)
        removed.append(str(path))

    print(f"SQLITE_CACHE_AUDIT checked={checked} removed={len(removed)}")
    return checked, len(removed), removed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=os.getenv("KEIBA_DATA_DIR", ".arvexq-data"),
        help="ARVEXQ cache directory",
    )
    args = parser.parse_args()
    sanitize(Path(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
