"""Existing circuit mapping and normalization; no guessed race data."""
from __future__ import annotations
from typing import Any

CIRCUITS = {
    "jra": "jra", "中央": "jra", "central": "jra",
    "nar": "nar", "地方": "nar", "local": "nar",
}


def normalize_circuit(value: Any) -> str | None:
    return CIRCUITS.get(str(value or "").strip().lower())
