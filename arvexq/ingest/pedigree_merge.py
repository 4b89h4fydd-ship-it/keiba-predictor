"""Fill ancestry gaps without replacing existing facts or hiding conflicts."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

ANCESTORS = ("sire", "dam", "damsire")


def present(value: Any) -> bool:
    return value not in (None, "", [], {}, "不明")


def needs_pedigree(horse: dict) -> bool:
    pedigree = horse.get("pedigree")
    pedigree = pedigree if isinstance(pedigree, dict) else {}
    return any(not present(pedigree.get(key)) and not present(horse.get(key))
               for key in ANCESTORS)


def fill_pedigree(horse: dict, payload: dict, *, source: str) -> bool:
    """Preserve both representations; record actual incoming facts and conflicts.

    acquiredAt is the ingestion time, NOT proof of historical publication time.
    A caller must not use this log as a pre-off seal.
    """
    nested = payload.get("pedigree")
    incoming = dict(nested) if isinstance(nested, dict) else {}
    for key in ANCESTORS:
        if not present(incoming.get(key)) and present(payload.get(key)):
            incoming[key] = payload[key]
    if not incoming:
        return False
    target = horse.get("pedigree")
    target = deepcopy(target) if isinstance(target, dict) else {}
    changed = False
    observations = horse.get("_pedigreeEvidence")
    observations = deepcopy(observations) if isinstance(observations, list) else []
    for key, value in incoming.items():
        if not present(value):
            continue
        existing = target.get(key)
        if not present(existing):
            existing = horse.get(key)
        conflict = present(existing) and existing != value
        if not present(existing):
            target[key] = deepcopy(value)
            changed = True
        observation = {"field": key, "source": source, "value": deepcopy(value),
                       "status": "conflict" if conflict else "observed"}
        if conflict:
            observation["retainedValue"] = deepcopy(existing)
        if not any(all(row.get(k) == v for k, v in observation.items())
                   for row in observations if isinstance(row, dict)):
            observation["acquiredAt"] = datetime.now(timezone.utc).isoformat()
            observations.append(observation)
            changed = True
    if target:
        horse["pedigree"] = target
    if observations:
        horse["_pedigreeEvidence"] = observations
    return changed
