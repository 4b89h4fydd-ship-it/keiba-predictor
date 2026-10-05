#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate disposable ARVEXQ SQLite cache files.

GitHub Actions restores .arvexq-data from cache archives. A stale/corrupt SQLite
file must never poison PREFETCH/LIVE/RESULT/HISTORY lanes. D1 remains the durable
application store; local SQLite files are rebuildable acceleration caches.

Only files with an actual SQLite file header are inspected. Non-SQLite JSON and
other cache assets are left untouched. With --delete-corrupt, only databases
that fail PRAGMA quick_check (plus their WAL/SHM sidecars) are removed.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

SQLITE_HEADER = b"SQLite format 3\x00"


def _is_sqlite(path: Path) -> bool:
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size < len(SQLITE_HEADER):
            return False
        with path.open("rb") as fh:
            return fh.read(len(SQLITE_HEADER)) == SQLITE_HEADER
    except OSError:
        return False


def _quick_check(path: Path) -> tuple[bool, str]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro&immutable=1"
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        rows = conn.execute("PRAGMA quick_check").fetchall()
        messages = [str(row[0]) for row in rows if row]
        ok = bool(messages) and all(message.lower() == "ok" for message in messages)
        return ok, "; ".join(messages) if messages else "quick_check returned no rows"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _remove_database(path: Path) -> list[str]:
    removed: list[str] = []
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        try:
            if candidate.exists() or candidate.is_symlink():
                candidate.unlink()
                removed.append(str(candidate))
        except OSError as exc:
            raise RuntimeError(f"cannot remove {candidate}: {exc}") from exc
    return removed


def scan(root: Path, *, delete_corrupt: bool = False) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    checked: list[str] = []
    healthy: list[str] = []
    corrupt: dict[str, str] = {}
    removed: list[str] = []
    errors: dict[str, str] = {}

    # Sidecars are always transient process-local state and are safe to discard
    # before opening the restored database files.
    for sidecar in list(root.rglob("*-wal")) + list(root.rglob("*-shm")):
        try:
            if sidecar.is_file() or sidecar.is_symlink():
                sidecar.unlink()
                removed.append(str(sidecar))
                print("CACHE_SIDECAR_REMOVED", sidecar)
        except OSError as exc:
            errors[str(sidecar)] = f"{type(exc).__name__}: {exc}"

    for path in sorted(root.rglob("*")):
        if not _is_sqlite(path):
            continue
        rel = str(path.relative_to(root))
        checked.append(rel)
        ok, message = _quick_check(path)
        if ok:
            healthy.append(rel)
            print("CACHE_DB_OK", rel)
            continue
        corrupt[rel] = message
        print("CACHE_DB_CORRUPT", rel, message)
        if delete_corrupt:
            try:
                removed.extend(_remove_database(path))
                print("CACHE_DB_DELETED", rel)
            except Exception as exc:
                errors[rel] = f"{type(exc).__name__}: {exc}"

    report: dict[str, Any] = {
        "root": str(root),
        "checked": checked,
        "healthy": healthy,
        "corrupt": corrupt,
        "removed": removed,
        "errors": errors,
        "checked_count": len(checked),
        "healthy_count": len(healthy),
        "corrupt_count": len(corrupt),
        "removed_count": len(removed),
    }
    print(
        "CACHE_HEALTH_AUDIT",
        f"checked={len(checked)}",
        f"healthy={len(healthy)}",
        f"corrupt={len(corrupt)}",
        f"removed={len(removed)}",
        f"errors={len(errors)}",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=os.getenv("KEIBA_DATA_DIR", ".arvexq-data"))
    parser.add_argument("--delete-corrupt", action="store_true")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    report = scan(Path(args.root), delete_corrupt=args.delete_corrupt)
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # If deletion was requested, a corrupt database is acceptable only when it
    # was actually removed. Operational errors are never silently ignored.
    if report["errors"]:
        return 2
    if report["corrupt_count"] and not args.delete_corrupt:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
