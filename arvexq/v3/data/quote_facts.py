"""Pure independent observed odds fields. Not implied probabilities or tickets.

Missing/no timestamp is not 'live', 'current', or a numeric zero.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from arvexq.v3.data.observed_fields import ensure_circuit

QUOTE_FIELDS = {
    "win_odds": "winOdds",
    "place_odds": "placeOdds",
    "popularity": "popularity",
}
# Only dedicated odds timestamps, never race updatedAt or wall-clock time.
TIME_KEYS = ("oddsUpdatedAt", "oddsTimestamp")


def _classification(field: str, value: Any) -> str:
    if value is None or isinstance(value, str) and value.strip() in ("", "-", "--", "不明"):
        return "missing"
    if isinstance(value, bool):
        return "invalid"
    if field == "quote_time":
        return "observed-unverified-timestamp" if (
            isinstance(value, (str, int, float)) and value not in ("", 0)
        ) else "invalid"
    if field == "place_odds" and isinstance(value, str) and "-" in value:
        # Provider-supplied range is retained as raw text, NOT reinterpreted
        # as a probability or fabricated decimal. Future schema verification.
        return "observed-raw-range"
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return "invalid"
    if not isfinite(numeric) or numeric <= 0:
        return "invalid"
    if field == "popularity" and (not numeric.is_integer() or
                                    isinstance(value, str) and not value.strip().isdigit()):
        return "invalid"
    return "observed"


def read_field(detail: dict[str, Any], circuit: str, field: str) -> list[dict]:
    ensure_circuit(detail, circuit)
    if field not in (*QUOTE_FIELDS, "quote_time"):
        raise ValueError("unknown odds observation field")
    horses = detail.get("horses")
    if not isinstance(horses, list):
        return []
    result = []
    for horse in horses:
        if not isinstance(horse, dict):
            continue
        source_key = None
        if field == "quote_time":
            source_key = next((key for key in TIME_KEYS if key in horse
                               and horse[key] not in (None, "")), None)
        else:
            source_key = QUOTE_FIELDS[field] if QUOTE_FIELDS[field] in horse else None
        value = deepcopy(horse.get(source_key)) if source_key else None
        state = _classification(field, value)
        result.append({
            "horseNumber": deepcopy(horse.get("horseNumber")),
            "status": state,
            "value": value if state.startswith("observed") else None,
            "sourceKey": source_key,
        })
    return result
