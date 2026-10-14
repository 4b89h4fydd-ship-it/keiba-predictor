"""Circuit-specific experimental horse-racing scores.

Both engines use only dated starts preceding the target race. The two scoring
rules deliberately differ: JRA uses recent-form momentum; NAR uses observed
same-track quality. The numerical weights are provisional, not calibrated
winning probabilities. No old three-factor fallback.
"""
from __future__ import annotations

from typing import Any

JRA_MODEL_VERSION = "arvexq-jra-momentum-condition-stage-v1"
NAR_MODEL_VERSION = "arvexq-nar-track-condition-stage-v1"


def circuit_key(race: dict[str, Any]) -> str:
    name = str(race.get("circuit") or race.get("raceCircuit") or "").strip().upper()
    if name in ("中央", "JRA", "CENTRAL"):
        return "JRA"
    if name in ("地方", "NAR", "LOCAL"):
        return "NAR"
    return "UNSPECIFIED"


def _quality(run: dict[str, Any]) -> float:
    return (float(run["fieldSize"]) - float(run["finish"])) / (float(run["fieldSize"]) - 1.0)


def _baseline(raw: dict[str, Any], condition_per_run: float, cap: float) -> float:
    recent = raw.get("recentForm")
    comparable = raw.get("conditionForm")
    if recent is None:
        return 0.5
    if comparable is None:
        return float(recent)
    strength = min(cap, condition_per_run * int(raw.get("conditionRuns") or 0))
    return (1.0 - strength) * float(recent) + strength * float(comparable)


def jra_score(raw: dict[str, Any], runs: list[dict[str, Any]]) -> float:
    """JRA: changes in finishing form plus conservative course/surface match."""
    score = _baseline(raw, 0.04, 0.12)
    if raw.get("recentForm") is not None and len(runs) >= 4:
        quality = [_quality(x) for x in runs]
        momentum = (quality[0] + quality[1] - quality[-1] - quality[-2]) / 2.0
        score += 0.06 * max(-0.30, min(0.30, momentum))
    return max(0.0, min(1.0, score))


def nar_score(raw: dict[str, Any], runs: list[dict[str, Any]], race: dict[str, Any]) -> float:
    """NAR: same-track results matter after independent condition adjustment."""
    score = _baseline(raw, 0.08, 0.25)
    track = str(race.get("track") or "").strip()
    if raw.get("recentForm") is not None and track:
        matched = [_quality(x) for x in runs
                   if str(x.get("track") or "").strip() == track]
        if len(matched) >= 2:
            same_track = sum(matched) / len(matched)
            score = 0.90 * score + 0.10 * same_track
    return max(0.0, min(1.0, score))
