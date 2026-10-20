"""Date-scoped central race summary deduplication; no transport or storage.

Inputs are existing summary dictionaries or observed card identifiers. Outputs
are keyed by venue/race number. Caller callbacks normalize summaries and decode
identifier fields. Invalid numeric values keep their existing conversion errors;
missing identities are skipped during fresh/discovery merging.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

SummaryKey = tuple[str, int]


def summary_key(row: Mapping[str, Any]) -> SummaryKey:
    return str(row.get("track") or ""), int(row.get("raceNumber") or 0)


def index_summaries(rows: Iterable[dict]) -> dict[SummaryKey, dict]:
    """Retain the last cached summary for each observed venue/race pair."""
    return {summary_key(row): dict(row) for row in rows}


def merge_refreshed_summaries(cached: Mapping[SummaryKey, dict], fresh: Iterable[dict],
                              normalize: Callable[[dict], dict | None]) -> dict[SummaryKey, dict]:
    """Refresh schedule facts in source order while retaining cached results."""
    merged = dict(cached)
    for row in fresh:
        key = summary_key(row)
        if not key[0] or not key[1]:
            continue
        previous = merged.get(key, {})
        result = dict(previous)
        for name, value in row.items():
            if name in {"horses", "result"}:
                continue
            if value not in (None, "", 0, []):
                result[name] = value
        if previous.get("result"):
            result["result"] = previous["result"]
        if previous.get("horses"):
            result["horses"] = []
        merged[key] = normalize(result) or result
    return merged


def choose_card_identifiers(identifiers: Iterable[str], track_of: Callable,
                            race_number_of: Callable) -> dict[SummaryKey, str]:
    """Keep the existing detailed-card preference among observed identifiers."""
    chosen = {}
    for identifier in identifiers:
        key = track_of(identifier), race_number_of(identifier)
        if not key[0] or not key[1]:
            continue
        if key not in chosen or identifier.startswith("pw01dde01"):
            chosen[key] = identifier
    return chosen
