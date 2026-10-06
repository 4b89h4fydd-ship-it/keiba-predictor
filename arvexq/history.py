"""Past-performance domain helpers.

ARVEXQ keeps exactly five recent runs for horse-detail presentation.  This
module normalizes the several legacy history keys into one stable shape.
"""
from __future__ import annotations

from typing import Any

_HISTORY_KEYS = ("recentRaces", "allPastRuns", "pastRaces", "history", "runs")


def _pick(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def normalize_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": _pick(run, "date", "raceDate", "日付") or "",
        "track": _pick(run, "track", "venue", "course", "競馬場") or "",
        "title": _pick(run, "title", "raceName", "name", "レース名") or "",
        "surface": _pick(run, "surface", "trackType", "馬場") or "",
        "distance": _pick(run, "distance", "distanceM", "距離") or None,
        "condition": _pick(run, "condition", "going", "馬場状態") or "",
        "finish": _pick(run, "finish", "finishPosition", "着順") or None,
        "time": _pick(run, "time", "raceTime", "タイム") or "",
        "passing": _pick(run, "passing", "cornerPositions", "通過順位") or "",
        "last3f": _pick(run, "last3f", "last600", "上がり") or None,
        "first1f": _pick(run, "first1f", "first200", "テン1F") or None,
        "carriedWeight": _pick(run, "carriedWeight", "weight", "斤量") or None,
        "bodyWeight": _pick(run, "bodyWeight", "horseWeight", "馬体重") or None,
        "fieldSize": _pick(run, "fieldSize", "runners", "頭数") or None,
        "opponentLevel": _pick(run, "opponentLevel", "classLevel", "相手レベル") or None,
        "index": _pick(run, "index", "performanceIndex", "指数") or None,
    }


def recent_runs(horse: dict[str, Any] | None, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(horse, dict):
        return []
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for key in _HISTORY_KEYS:
        values = horse.get(key)
        if not isinstance(values, list):
            continue
        for raw in values:
            if not isinstance(raw, dict):
                continue
            run = normalize_run(raw)
            fingerprint = (
                str(run.get("date") or ""),
                str(run.get("track") or ""),
                str(run.get("title") or ""),
                str(run.get("finish") or ""),
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            candidates.append(run)
    candidates.sort(key=lambda x: str(x.get("date") or ""), reverse=True)
    return candidates[: max(0, int(limit))]


def has_history(horse: dict[str, Any] | None) -> bool:
    if not isinstance(horse, dict):
        return False
    if horse.get("debutNoHistory"):
        return True
    return bool(recent_runs(horse, 1))


__all__ = ["has_history", "normalize_run", "recent_runs"]
