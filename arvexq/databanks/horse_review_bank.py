"""Race-by-race observed review databank. No subjective inference without evidence."""
from __future__ import annotations
from typing import Any


def build_horse_review_bank(recaps: list[dict[str, Any]]) -> dict[str, Any]:
    horses: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()
    for recap in recaps:
        if not isinstance(recap, dict) or recap.get("verifiedFrom") != "settled-result-payload":
            continue
        race_id = str(recap.get("raceId") or "")
        for runner in recap.get("finishers") or []:
            if not isinstance(runner, dict):
                continue
            key = str(runner.get("horseId") or "")
            # Race-number-only identifiers are NOT safe to join across races.
            if not key or not race_id:
                continue
            pair = (race_id, key)
            if pair in seen:
                continue
            seen.add(pair)
            horses.setdefault(key, []).append({
                "raceId": race_id, "date": recap.get("date"),
                "finish": runner.get("finish"), "observedNote": runner.get("note"),
                "source": "settled-result-only", "videoVerified": False,
            })
    for runs in horses.values():
        runs.sort(key=lambda z: (str(z.get("date") or ""), z["raceId"]), reverse=True)
    return {
        "version": "arvexq-horse-review-bank-v1",
        "horses": horses,
        "unlinkedWithoutStableHorseId": True,
        "predictiveCalibrationStatus": "not-tested",
    }
