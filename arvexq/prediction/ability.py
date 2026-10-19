"""Retained compatibility API; rejected legacy ability ranking is deleted.

No scores or predictions are produced. Factual evidence is maintained elsewhere.
"""
from __future__ import annotations
from typing import Any, Iterable


def horse_evidence(h: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    return {"margin": None, "marginCoverage": 0, "modelVersion": None}


def rank_ability(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    return []


def apply_ability_ranking(detail: dict[str, Any]) -> dict[str, Any]:
    detail.pop("abilityRanking", None)
    detail.pop("abilityRankingModelVersion", None)
    for horse in detail.get("horses") or []:
        if isinstance(horse, dict):
            horse.pop("abilityEvidence", None)
    return detail
