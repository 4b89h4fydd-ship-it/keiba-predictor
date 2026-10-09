"""Deterministic, verifiable post-race review; NEVER rewrite a pre-off ticket."""
from __future__ import annotations
from typing import Any

VERSION = "arvexq-observed-race-review-v1"


def build_race_recap(detail: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(detail, dict):
        return None
    result = detail.get("result") or {}
    if not isinstance(result, dict):
        return None
    status = str(result.get("status") or detail.get("raceStatus") or "")
    if not any(v in status for v in ("確定", "official", "final", "FINAL")):
        return None
    finishers = result.get("finishers") or []
    if not isinstance(finishers, list):
        return None
    horses = {str(h.get("horseNumber")): h for h in (detail.get("horses") or [])
              if isinstance(h, dict) and h.get("horseNumber")}
    entries = []
    for row in finishers:
        if not isinstance(row, dict):
            continue
        try:
            position = int(row.get("finish", row.get("finishPosition")))
            number = int(row.get("horseNumber"))
        except (ValueError, TypeError):
            continue
        if position <= 0 or number <= 0:
            continue
        horse = horses.get(str(number), {})
        name = str(row.get("name") or row.get("horseName") or horse.get("name") or "").strip()
        corners = row.get("cornerPositions")
        corners = corners if isinstance(corners, list) else []
        note = f"{position}着"
        if corners:
            note += "／通過順位 " + "-".join(str(x) for x in corners if x is not None)
        if not name:
            name = f"{number}番"
        entries.append({
            "horseNumber": number, "horseId": horse.get("horseId") or horse.get("id"),
            "horseName": name, "finish": position, "note": note,
            "source": "result-finishers",
        })
    if len(entries) < 3:
        return None
    entries.sort(key=lambda x: (x["finish"], x["horseNumber"]))
    top = entries[:3]
    summary = ("・".join(f"{h['horseNumber']}番{h['horseName']}" for h in top)
               + " が1〜3着。確定着順データから作成した回顧（映像未確認）。")
    return {
        "version": VERSION, "raceId": str(detail.get("id") or ""),
        "date": str(detail.get("date") or ""), "track": str(detail.get("track") or ""),
        "finishers": entries, "summary": summary,
        "verifiedFrom": "settled-result-payload", "videoVerified": False,
        "preoffForecastWasChanged": False,
    }
