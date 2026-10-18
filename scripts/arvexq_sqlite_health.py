#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify restored ARVEXQ SQLite caches without discarding evidence.

A WAL can contain COMMITTED transactions not yet checkpointed into the main
database. Never delete SQLite databases, WALs or journals as a health action.
Any corruption, lock contention or read-only condition fails closed while
preserving the original bytes for diagnosis.
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
            value = str(row[0] if row else "").strip().lower()
            if value != "ok":
                return False, value or "empty quick_check result"
            # quick_check works on a read-only cache too. Probe the same write
            # lock later used by collectors without modifying user tables.
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("ROLLBACK")
            return True, "ok"
        finally:
            conn.close()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def sanitize(root: Path) -> tuple[int, int, list[str]]:
    root.mkdir(parents=True, exist_ok=True)
    if not os.access(root, os.W_OK):
        raise PermissionError(f"SQLite cache directory is not writable: {root}")

    # A SQLite -wal sidecar can contain the most recent committed race facts.
    # SQLite itself owns checkpointing; removing sidecars is data loss.
    checked = 0
    blocked: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if not _looks_sqlite(path):
            continue
        checked += 1
        ok, reason = _quick_check(path)
        if ok:
            print("SQLITE_CACHE_OK", path)
            continue
        print("SQLITE_CACHE_UNAVAILABLE_PRESERVED", path, reason)
        blocked.append(f"{path}: {reason}")
    print(f"SQLITE_CACHE_AUDIT checked={checked} removed=0 blocked={len(blocked)}")
    if blocked:
        raise RuntimeError("SQLite cache cannot be safely used; original files preserved: "
                           + "; ".join(blocked[:5]))
    return checked, 0, []


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
