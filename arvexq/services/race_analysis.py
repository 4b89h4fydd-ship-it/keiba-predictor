from __future__ import annotations

from typing import Any

from arvexq.features.horse_features import attach_race_features
from arvexq.ingest.source_merge import merge_race_sources
from arvexq.normalize.race import normalize_race
from arvexq.prediction.ability import apply_ability_ranking
from arvexq.prediction.confidence import build_win_confidence_evidence


def normalize_race_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return normalize_race(detail)


def prepare_race_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """Single orchestration boundary for pre-race analysis.

    Flow: source merge -> canonical normalization -> ability/record ranking ->
    inspectable features -> raw win-confidence evidence. Source adapters and UI code
    stay outside the prediction core.
    """
    if not isinstance(detail, dict):
        return detail
    detail = merge_race_sources(detail)
    detail = normalize_race(detail)
    detail = apply_ability_ranking(detail)
    detail = attach_race_features(detail)
    detail["winConfidenceEvidence"] = build_win_confidence_evidence(detail.get("abilityRanking") or [])
    return detail
