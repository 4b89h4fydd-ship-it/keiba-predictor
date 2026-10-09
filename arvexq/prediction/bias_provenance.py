"""Distinguish official surface conditions from estimated track bias."""
from __future__ import annotations

from typing import Any

VERSION = "arvexq-bias-provenance-v1"


def provenance(race: dict[str, Any]) -> dict[str, Any]:
    official = race.get("officialCourseReport")
    official = official if isinstance(official, dict) else {}
    # Surface condition on a race card is not itself an official 'inside advantage' report.
    condition = official.get("condition") or race.get("condition") or race.get("going")
    condition_source = "official-announcement" if official.get("condition") else "race-card-unverified"
    estimated = race.get("aiTrackBias") or race.get("trackBiasEstimate")
    if not isinstance(estimated, dict):
        estimated = {}
    return {
        "version": VERSION,
        "official": {
            "condition": condition, "source": condition_source,
            "issuedAt": official.get("issuedAt") if official.get("condition") else None,
            "weather": official.get("weather") or race.get("weather"),
        },
        "estimated": {
            "frontBack": estimated.get("frontBack"),
            "insideOutside": estimated.get("insideOutside"),
            "sampleRaces": estimated.get("sampleRaces"),
            "source": "ai-inference-not-official",
        },
        "changesMorningMarks": False,
        "revisionPolicy": "Only confirmed material official course updates can authorize a pre-off mark revision.",
    }
