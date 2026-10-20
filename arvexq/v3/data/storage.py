"""Read an existing saved race without starting a second retrieval/storage route."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


def read_existing_snapshot(getter: Callable[[str], Any], race_id: str) -> dict | None:
    """Use an injected existing cache/D1 getter. No fetch, write or fallback.

    Existing stores may return either detail or (detail, saved_at_epoch).
    Never let one race's payload pass through a different requested race ID.
    """
    if not isinstance(race_id, str) or not race_id:
        raise ValueError("race_id required")
    value = getter(race_id)
    if isinstance(value, tuple):
        value = value[0] if value else None
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("invalid saved snapshot")
    if str(value.get("id") or "") != race_id:
        raise ValueError("saved snapshot race identity mismatch")
    return deepcopy(value)
