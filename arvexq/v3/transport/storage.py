"""Use ONLY the existing saved race getter. No direct D1/SQLite writer."""
from __future__ import annotations

from typing import Any, Callable

from arvexq.v3.data.storage import read_existing_snapshot
from arvexq.v3.data.observed_fields import ensure_circuit
from arvexq.v3.data.quality import normalize_circuit


def read_saved(getter: Callable[[str], Any], race_id: str, *, circuit: str) -> dict | None:
    """Delegate to existing authoritative store, preserving original payload."""
    name = normalize_circuit(circuit)
    if name is None:
        raise ValueError("unknown racing circuit")
    if not isinstance(race_id, str) or not race_id.startswith(name + "-"):
        raise ValueError("race id/circuit mismatch")
    saved = read_existing_snapshot(getter, race_id)
    if saved is None:
        return None
    ensure_circuit(saved, name)
    return saved
