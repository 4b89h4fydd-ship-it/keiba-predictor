"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

import re
from arvexq.normalize.scalars import _clean


def _horse_key(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", _clean(str(value or "")))


def _central_find_horse(race: dict, horse_name: str) -> tuple[dict | None, dict | None]:
    key = _horse_key(horse_name)
    horse = None
    for h in race.get("horses", []) or []:
        if _horse_key(h.get("name")) == key:
            horse = h
            break
    finisher = None
    result = race.get("result") if isinstance(race.get("result"), dict) else {}
    finishers = result.get("finishers") if isinstance(result.get("finishers"), list) else []
    for f in finishers:
        same_no = horse is not None and int(f.get("horseNumber") or 0) == int(horse.get("horseNumber") or 0)
        same_name = _horse_key(f.get("name")) == key
        if same_no or same_name:
            finisher = f
            break
    return horse, finisher


def _central_run_from_race(race: dict, horse_name: str) -> dict | None:
    horse, fin = _central_find_horse(race, horse_name)
    if horse is None and fin is None:
        return None
    horse = horse or {}
    fin = fin or {}
    finish = int(fin.get("finish") or horse.get("finish") or 0)
    corners = fin.get("cornerPositions") or horse.get("cornerPositions") or []
    if not isinstance(corners, list):
        corners = []
    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f = fin.get("last3FSeconds") or fin.get("last3F") or horse.get("last3FSeconds") or horse.get("last3F")
    try:last3f=float(last3f) if last3f not in (None,"") else None
    except (TypeError,ValueError):last3f=None
    last3f_rank=fin.get("last3FRank") or horse.get("last3FRank")
    try:last3f_rank=int(last3f_rank) if last3f_rank not in (None,"") else None
    except (TypeError,ValueError):last3f_rank=None
    last3f_pct=fin.get("last3FPercentile") if fin.get("last3FPercentile") is not None else horse.get("last3FPercentile")
    try:last3f_pct=float(last3f_pct) if last3f_pct is not None else None
    except (TypeError,ValueError):last3f_pct=None
    return {
        "raceId": race.get("id") or "",
        "date": race.get("date") or "",
        "track": race.get("track") or "",
        "raceNumber": int(race.get("raceNumber") or 0),
        "title": race.get("title") or "",
        "distance": int(race.get("distance") or 0),
        "condition": race.get("condition") or "不明",
        "weather": race.get("weather") or "不明",
        "surface": race.get("surface") or "",
        "fieldSize": int(race.get("fieldSize") or len(race.get("horses") or [])),
        "finish": finish,
        "timeSeconds": float(fin.get("timeSeconds") or horse.get("timeSeconds") or 0),
        "last3FSeconds": last3f,
        "last3FRank": last3f_rank,
        "last3FPercentile": last3f_pct,
        "cornerPositions": [int(x) for x in corners if str(x).strip().isdigit()],
        "carriedWeight": float(horse.get("carriedWeight") or fin.get("carriedWeight") or 0),
        "racePrize1": int(race.get("racePrize1") or 0),
        "jockey": horse.get("jockey") or fin.get("jockey") or "",
        "trainer": horse.get("trainer") or fin.get("trainer") or "",
        "source": race.get("source") or "中央フィード",
    }

