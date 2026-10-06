"""Race-condition domain helpers."""
from __future__ import annotations

from typing import Any


def _pick(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def build_race_conditions(race: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(race, dict):
        return {}
    return {
        "track": _pick(race, "track", "venue", "course", "競馬場") or "",
        "surface": _pick(race, "surface", "trackType", "馬場") or "",
        "distance": _pick(race, "distance", "distanceM", "距離") or None,
        "condition": _pick(race, "condition", "going", "trackCondition", "馬場状態") or "",
        "weather": _pick(race, "weather", "天候") or "",
        "direction": _pick(race, "direction", "courseDirection", "回り") or "",
        "layout": _pick(race, "courseLayout", "layout", "courseShape", "コース形状") or None,
        "startTime": _pick(race, "startTime", "postTime", "発走") or "",
    }


__all__ = ["build_race_conditions"]
