from __future__ import annotations

from typing import Any

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import observed_runs, analyze_past_performance


def build_horse_features(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    runs = observed_runs(horse, race)
    past = analyze_past_performance(horse, race)
    finishes = [float(r.get("finish")) for r in runs if isinstance(r.get("finish"), (int, float)) and float(r.get("finish")) > 0]
    same_distance = [r for r in runs if r.get("distance") == race.get("distance")]
    same_track = [r for r in runs if r.get("track") and r.get("track") == race.get("track")]
    same_condition = [r for r in runs if r.get("condition") and r.get("condition") == race.get("condition")]
    evidence = horse.get("abilityEvidence") if isinstance(horse.get("abilityEvidence"), dict) else {}
    return {
        "horseNumber": int(horse.get("horseNumber") or 0),
        "inactive": is_inactive_runner(horse),
        "historySamples": len(runs),
        "pastPerformance": past,
        "bestFinish5": int(min(finishes)) if finishes else None,
        "averageFinish5": round(sum(finishes) / len(finishes), 3) if finishes else None,
        "sameDistanceSamples5": len(same_distance),
        "sameTrackSamples5": len(same_track),
        "sameConditionSamples5": len(same_condition),
        "sourceCount": int(horse.get("_sourceCount") or 1),
        "abilityRank": evidence.get("rank"),
        "abilityScore": evidence.get("score"),
        "abilityComponents": evidence.get("components") or {},
    }


def attach_race_features(detail: dict[str, Any]) -> dict[str, Any]:
    detail["horseFeatures"] = [
        build_horse_features(h, detail)
        for h in (detail.get("horses") or [])
        if isinstance(h, dict)
    ]
    return detail
