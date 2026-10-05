from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class HorseSourceRecord:
    source: str
    horse_key: str
    values: dict[str, Any] = field(default_factory=dict)
    observed_at: str | None = None
    priority: int = 100


def merge_horse_records(records: list[HorseSourceRecord]) -> dict[str, Any]:
    """Merge multiple horse-data sources without silently overwriting stronger evidence.

    Lower priority number wins. Empty values never replace populated values. Conflicting
    values are retained in `_sourceEvidence` so prediction code can inspect disagreement.
    """
    merged: dict[str, Any] = {}
    source_evidence: dict[str, list[dict[str, Any]]] = {}

    for record in sorted(records, key=lambda r: (r.priority, r.source)):
        for key, value in record.values.items():
            if value in (None, "", [], {}):
                continue
            source_evidence.setdefault(key, []).append({
                "source": record.source,
                "value": value,
                "observedAt": record.observed_at,
                "priority": record.priority,
            })
            if key not in merged or merged[key] in (None, "", [], {}):
                merged[key] = value

    merged["_sourceEvidence"] = source_evidence
    merged["_sourceCount"] = len({r.source for r in records})
    return merged


def attach_source_record(horse: dict[str, Any], record: HorseSourceRecord) -> dict[str, Any]:
    bucket = horse.setdefault("_sourceRecords", [])
    bucket.append({
        "source": record.source,
        "horseKey": record.horse_key,
        "values": record.values,
        "observedAt": record.observed_at,
        "priority": record.priority,
    })
    return horse
