"""Canonical responsibility 146: observed factual cache identity only, no storage operations."""
from __future__ import annotations

from arvexq.storage.cache_keys import race_detail_key
from arvexq.v3.data.quality import normalize_circuit

def factual_cache_key(race_id: str, circuit: str) -> str:
    name = normalize_circuit(circuit)
    if name is None or not isinstance(race_id, str) or not race_id:
        raise ValueError("valid race identity and circuit required")
    # The only supported v3 race IDs are circuit-prefixed canonical identities.
    if not race_id.startswith(name + "-"):
        raise ValueError("race id/circuit mismatch")
    return race_detail_key(race_id, version="v3-factual-observed")
