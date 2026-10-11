"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

from arvexq.normalize.scalars import _clean, _int


def normalize_central_race(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    date = _clean(str(raw.get("date") or ""))
    track = _clean(str(raw.get("track") or ""))
    race_no = _int(str(raw.get("raceNumber") or raw.get("race_no") or "0"))
    if not date or not track or race_no <= 0:
        return None
    horses = raw.get("horses") if isinstance(raw.get("horses"), list) else []
    rid = _clean(str(raw.get("id") or f"jra-{date}-{track}-{race_no:02d}"))
    out = dict(raw)
    out.update({
        "id": rid, "circuit": "中央", "date": date, "track": track, "raceNumber": race_no,
        "title": raw.get("title") or f"{race_no}R", "distance": int(raw.get("distance") or 0),
        "condition": raw.get("condition") or "不明", "weather": raw.get("weather") or "不明",
        "surface": raw.get("surface") or raw.get("trackType") or "",
        "fieldSize": int(raw.get("fieldSize") or len(horses)),
        "racePrize1": int(raw.get("racePrize1") or raw.get("prize1") or 0),
        "startTime": raw.get("startTime") or raw.get("actualStartTime") or "",
        "scheduledStartTime": raw.get("scheduledStartTime") or raw.get("originalStartTime") or raw.get("startTime") or raw.get("actualStartTime") or "",
        "horses": horses, "source": raw.get("source") or "中央本番フィード",
    })
    out["startTimeChanged"] = bool(out.get("scheduledStartTime") and out.get("startTime") and out.get("scheduledStartTime") != out.get("startTime"))
    return out

