from __future__ import annotations

from copy import deepcopy
from typing import Any

from arvexq.databanks.merge import HorseSourceRecord, merge_horse_records

SOURCE_PRIORITY = {
    "jra_official": 10,
    "nar_official": 10,
    "jbis": 20,
    "manual": 30,
    "supplemental": 50,
}


def _records(horse: dict[str, Any]) -> list[HorseSourceRecord]:
    out: list[HorseSourceRecord] = []
    horse_key = str(horse.get("horseId") or horse.get("id") or horse.get("name") or "")
    for raw in horse.get("_sourceRecords") or []:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "supplemental")
        values = raw.get("values") if isinstance(raw.get("values"), dict) else {}
        out.append(HorseSourceRecord(
            source=source,
            horse_key=str(raw.get("horseKey") or horse_key),
            values=values,
            observed_at=raw.get("observedAt"),
            priority=int(raw.get("priority") or SOURCE_PRIORITY.get(source, 50)),
        ))
    return out


def merge_horse_sources(horse: dict[str, Any]) -> dict[str, Any]:
    h = deepcopy(horse)
    records = _records(h)
    if not records:
        h.setdefault("_sourceCount", 1)
        return h
    merged = merge_horse_records(records)
    evidence = merged.pop("_sourceEvidence", {})
    count = merged.pop("_sourceCount", len(records))
    # Current canonical data stays authoritative; source records fill gaps only.
    for key, value in merged.items():
        if h.get(key) in (None, "", [], {}):
            h[key] = value
    h["_sourceEvidence"] = evidence
    h["_sourceCount"] = count
    return h


def merge_race_sources(detail: dict[str, Any]) -> dict[str, Any]:
    race = deepcopy(detail)
    race["horses"] = [merge_horse_sources(h) for h in (race.get("horses") or []) if isinstance(h, dict)]
    return race
