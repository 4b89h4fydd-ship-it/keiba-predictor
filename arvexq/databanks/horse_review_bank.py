"""Race-by-race observed review databank. No subjective inference without evidence."""
from __future__ import annotations
from typing import Any


def build_horse_review_bank(recaps: list[dict[str, Any]]) -> dict[str, Any]:
    horses: dict[str, list[dict[str, Any]]] = {}
    unlinked: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    seen_unlinked: set[tuple[str, int]] = set()
    for recap in recaps:
        if not isinstance(recap, dict) or recap.get("verifiedFrom") != "settled-result-payload":
            continue
        race_id = str(recap.get("raceId") or "")
        for runner in recap.get("finishers") or []:
            if not isinstance(runner, dict):
                continue
            key = str(runner.get("horseId") or "")
            # Race-number-only identifiers are NOT safe to join across races.
            if not race_id:
                continue
            if not key:
                try:
                    race_number = int(runner.get("horseNumber") or 0)
                except (TypeError, ValueError):
                    race_number = 0
                if race_number <= 0 or (race_id, race_number) in seen_unlinked:
                    continue
                seen_unlinked.add((race_id, race_number))
                # Preserve observed facts with race-local identity, but never
                # pretend a horse number is a global horse identifier.
                unlinked.append({
                    "raceId": race_id, "date": recap.get("date"),
                    "horseNumber": runner.get("horseNumber"),
                    "horseName": runner.get("horseName"),
                    "finish": runner.get("finish"), "observedNote": runner.get("note"),
                    "source": "settled-result-only", "requiresStableHorseId": True,
                })
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
        "unlinkedObservations": unlinked,
        "unlinkedWithoutStableHorseId": True,
        "predictiveCalibrationStatus": "not-tested",
    }
