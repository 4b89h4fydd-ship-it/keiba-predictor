#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bound SQLite busy waits for parallel ARVEXQ ingestion.

Install *before importing app*. Retain SQLite's transaction semantics: no
unbounded retries, suppressed errors, auto-commits or in-flight DB rewrites.
The importer must still restrict write concurrency. The guard is deliberately
opt-in for GitHub ingestion jobs; it does not affect web or local clients.
"""
from __future__ import annotations

import sqlite3
from typing import Any

_DEFAULT_BUSY_SECONDS = 30.0
_ORIGINAL_CONNECT = sqlite3.connect


def install(minimum_timeout: float = _DEFAULT_BUSY_SECONDS) -> None:
    """Ensure that short sqlite defaults do not fail under brief writer locks."""
    if getattr(sqlite3.connect, "_arvexq_guard_installed", False):
        return
    minimum_timeout = max(1.0, float(minimum_timeout))
    original = sqlite3.connect

    def connect(database: Any, *args: Any, **kwargs: Any):
        positional = list(args)
        if positional:
            try:
                wait = max(minimum_timeout, float(positional[0]))
            except (TypeError, ValueError):
                wait = minimum_timeout
            positional[0] = wait
        else:
            try:
                wait = max(minimum_timeout, float(kwargs.get("timeout", 5.0)))
            except (TypeError, ValueError):
                wait = minimum_timeout
            kwargs["timeout"] = wait
        connection = original(database, *positional, **kwargs)
        # Preserve longer per-caller timeouts; never shorten them here.
        connection.execute(f"PRAGMA busy_timeout={round(wait * 1000)}")
        return connection

    connect._arvexq_guard_installed = True
    sqlite3.connect = connect


def install_app_compat(app_module: Any) -> None:
    """Protect historical NAR result parsing from the absent legacy symbol."""
    if not hasattr(app_module, "last3f"):
        app_module.last3f = None
