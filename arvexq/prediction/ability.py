"""Observed ability evidence from the same authoritative JRA/NAR 60/40 ranker.

This is a read-only view, never a second scorer or an old-score fallback.
"""
from __future__ import annotations
from typing import Any, Iterable
from arvexq.prediction.observed_model import rank_observed, model_version
from arvexq.research.margin_abcde_candidate import score as margin_score


def horse_evidence(h: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    margin = margin_score(h, race)
    return {"margin": margin["score"] if margin is not None else None,
            "marginCoverage": margin["coverage"] if margin is not None else 0,
            "modelVersion": model_version(race)}


def rank_ability(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    ranked = rank_observed(list(horses), race)
    return [{
        "horse": row["horse"], "evidence": dict(row["factors"]),
        "components": dict(row["factors"]),
        "abilityScore": round(row["score"]*100,2),
        "evidenceWins": sum(row["score"] > other["score"] for other in ranked),
        "evidenceWeak": sum(row["score"] < other["score"] for other in ranked),
        "sample": row["sample"], "abilityRank": row["rank"],
        "pillarRanks": {}, "evidenceCounts": {"mineta":1, "margin":1},
        "supportTieBreakWins": 0, "modelVersion": model_version(race)
    } for row in ranked]


def apply_ability_ranking(detail: dict[str, Any]) -> dict[str, Any]:
    ranked=rank_ability(detail.get("horses") or [],detail)
    by_no={int(r["horse"].get("horseNumber") or 0):r for r in ranked}
    for horse in detail.get("horses") or []:
        row=by_no.get(int(horse.get("horseNumber") or 0))
        if row is not None:
            horse["abilityEvidence"]={
                "rank":row["abilityRank"],"score":row["abilityScore"],
                "scoreMeaning":"observed 60/40 score, not hit probability",
                "sample":row["sample"],"components":row["components"],
                "modelVersion":row["modelVersion"],
            }
    detail["abilityRanking"]=[
        {"horseNumber":int(r["horse"].get("horseNumber") or 0),
         "name":r["horse"].get("name") or "",
         "rank":r["abilityRank"],"score":r["abilityScore"],
         "sample":r["sample"],"components":r["components"],
         "modelVersion":r["modelVersion"]}
        for r in ranked
    ]
    detail["abilityRankingModelVersion"]=model_version(detail)
    return detail
