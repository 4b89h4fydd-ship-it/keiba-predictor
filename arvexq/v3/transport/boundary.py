"""Small service-facing factual boundary metadata, no duplication of race payloads."""
from __future__ import annotations

from typing import Any

from arvexq.v3.data.quality import normalize_circuit
from arvexq.v3.transport.cache import factual_cache_key


def read_boundary(detail: dict[str, Any] | None) -> dict[str, Any]:
    data = detail if isinstance(detail, dict) else {}
    circuit = normalize_circuit(data.get("circuit"))
    rid = str(data.get("id") or "")
    result = {
        "schema": "arvexq-v3-read-boundary-1",
        "circuit": circuit,
        "cacheKey": None,
        "storage": "existing-authoritative-snapshot-only",
        "apiAdapter": "read-only-not-routed",
        "screenAdapter": "read-only-not-wired",
        "predictionStatus": "not-implemented",
    }
    try:
        result["cacheKey"] = factual_cache_key(rid, circuit or "")
    except ValueError:
        result["identityStatus"] = "unavailable"
    else:
        result["identityStatus"] = "routed"
    return result
