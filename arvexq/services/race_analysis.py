from __future__ import annotations

from typing import Any

from arvexq.components.item_110.diagnosis import build_diagnosis
from arvexq.components.item_088.horse_features import attach_race_features
from arvexq.components.item_181.horse_detail import build_horse_details
from arvexq.components.item_040.source_merge import merge_race_sources
from arvexq.components.item_040.race import normalize_race
from arvexq.components.item_068.odds import build_odds_snapshot
from arvexq.components.item_105.pace_prediction import build_pace_prediction
from arvexq.components.item_089.ability import apply_ability_ranking
from arvexq.components.item_115.confidence import build_win_confidence_evidence
from arvexq.components.item_180.race_card import build_race_card
from arvexq.components.item_017.race_conditions import build_race_conditions


def normalize_race_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return normalize_race(detail)


def prepare_race_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """Single orchestration boundary for pre-race analysis.

    The legacy application still owns acquisition, but feature responsibilities
    are separated here: race card, conditions, odds, horse detail/history,
    diagnosis and pace prediction are independent domains. Prediction and
    betting remain separate cores.
    """
    if not isinstance(detail, dict):
        return detail
    detail = merge_race_sources(detail)
    detail = normalize_race(detail)
    detail = apply_ability_ranking(detail)
    detail = attach_race_features(detail)
    detail["winConfidenceEvidence"] = build_win_confidence_evidence(detail.get("abilityRanking") or [])

    # Additive domain views keep legacy API/UI compatibility while migration out
    # of app.py proceeds.  None of these helpers perform network access.
    detail["raceCardView"] = build_race_card(detail)
    detail["raceConditionsView"] = build_race_conditions(detail)
    detail["oddsView"] = build_odds_snapshot(detail)
    detail["horseDetailView"] = build_horse_details(detail)
    detail["diagnosisView"] = build_diagnosis(detail)
    detail["pacePredictionView"] = build_pace_prediction(detail)
    return detail
