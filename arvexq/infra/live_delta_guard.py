"""Read-only live detail change classifier that avoids D1 large-row rewrite on odds ticks.

Only market odds are separately persisted by the odds_current pipeline.
Any weather, scratch, body weight, result, prediction, seal, or history change
must still publish the full protected detail. This does not change predictions.
"""
from __future__ import annotations
import copy
import hashlib
import json
from typing import Any

TOP_MARKET_FIELDS = frozenset({"oddsSource", "oddsType", "oddsUpdatedAt"})
HORSE_MARKET_FIELDS = frozenset({"winOdds", "popularity", "oddsForecast", "oddsSource"})
META_VOLATILE_FIELDS = frozenset({"liveUpdatedAtEpoch"})


def persistent_projection(detail: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(detail)
    for key in TOP_MARKET_FIELDS:
        out.pop(key, None)
    meta = out.get("preparedMeta")
    if isinstance(meta, dict):
        for key in META_VOLATILE_FIELDS:
            meta.pop(key, None)
    for horse in out.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        for key in HORSE_MARKET_FIELDS:
            horse.pop(key, None)
    return out


def durable_fingerprint(detail: dict[str, Any]) -> str:
    core = persistent_projection(detail)
    raw = json.dumps(core, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def requires_full_write(previous: Any, current: Any) -> bool:
    if not isinstance(current, dict) or not current.get("id"):
        return False
    if not isinstance(previous, dict) or str(previous.get("id") or "") != str(current["id"]):
        return True
    return durable_fingerprint(previous) != durable_fingerprint(current)
