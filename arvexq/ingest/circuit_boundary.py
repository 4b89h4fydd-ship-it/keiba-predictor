"""Shared pre-off circuit and temporal boundary contracts.

This module contains factual guards only.  It does not score runners, fill
missing values, or produce forecasts, marks, probabilities, or tickets.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Iterable

from arvexq.ingest.circuit_transfer import _observed_day, race_circuit


def normalized_circuit(value: Any) -> str | None:
    """Return the public circuit label, without guessing unknown values."""
    text = str(value or "").strip().lower()
    if text in {"中央", "jra", "central"}:
        return "中央"
    if text in {"地方", "nar", "local"}:
        return "地方"
    return None


def record_circuit(record: dict[str, Any] | None) -> str | None:
    """Resolve a record's circuit from an explicit value or known venue."""
    if not isinstance(record, dict):
        return None
    explicit = normalized_circuit(record.get("circuit") or record.get("organization"))
    if explicit:
        return explicit
    observed = race_circuit(record)
    return {"JRA": "中央", "NAR": "地方"}.get(observed)


def compatible_with(record: dict[str, Any] | None, expected: str) -> bool:
    """Whether a record is safe to pass to an expected-circuit parser."""
    expected_label = normalized_circuit(expected)
    if expected_label is None or not isinstance(record, dict):
        return False
    actual = record_circuit(record)
    return actual is None or actual == expected_label


def require_compatible(record: dict[str, Any] | None, expected: str) -> None:
    """Reject an explicitly contradictory circuit before normalization."""
    if not compatible_with(record, expected):
        raise ValueError(f"circuit boundary violation: expected {expected!r}")


def before_cutoff(record: dict[str, Any] | None, cutoff: date | str | None) -> bool:
    """Accept only a valid observed date strictly before the target date."""
    if not isinstance(record, dict) or cutoff is None:
        return False
    target = cutoff if isinstance(cutoff, date) else _observed_day(cutoff)
    observed = _observed_day(record.get("date") or record.get("raceDate"))
    return bool(target and observed and observed < target)


def preoff_records(
    records: Iterable[dict[str, Any]],
    cutoff: date | str,
    *,
    circuit: str | None = None,
) -> list[dict[str, Any]]:
    """Copy comparable historical facts without mutation or imputation."""
    expected = normalized_circuit(circuit) if circuit else None
    output: list[dict[str, Any]] = []
    for record in records or []:
        if not before_cutoff(record, cutoff):
            continue
        if expected and record_circuit(record) not in {None, expected}:
            continue
        output.append(deepcopy(record))
    return output

