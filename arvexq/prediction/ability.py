from __future__ import annotations

from typing import Any, Iterable

from arvexq.prediction.factor_model import (
    MODEL_VERSION,
    collect_horse_raw_metrics,
    rank_factor_model,
)


def horse_evidence(h: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    """Compatibility view of the current pre-race evidence collector."""
    return collect_horse_raw_metrics(h, race)


def rank_ability(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    """Compatibility ranking backed by the four-pillar consensus model.

    `abilityScore` is a within-race head-to-head dominance score, not a win probability.
    No arbitrary percentage blend of factors is used to create the final order.
    """
    ranked = rank_factor_model(horses, race)
    out: list[dict[str, Any]] = []
    for row in ranked:
        out.append(
            {
                "horse": row["horse"],
                "evidence": row["raw"],
                "components": row["pillarScores"],
                "abilityScore": row["dominanceScore"],
                "evidenceWins": row["pairwiseWins"],
                "evidenceWeak": row["pairwiseLosses"],
                "sample": row["sample"],
                "abilityRank": row["rank"],
                "pillarRanks": row["pillarRanks"],
                "evidenceCounts": row["evidenceCounts"],
                "supportTieBreakWins": row["supportTieBreakWins"],
                "modelVersion": MODEL_VERSION,
            }
        )
    return out


def apply_ability_ranking(detail: dict[str, Any]) -> dict[str, Any]:
    horses = detail.get("horses") or []
    ranked = rank_ability(horses, detail)
    by_no = {int(r["horse"].get("horseNumber") or 0): r for r in ranked}
    for h in horses:
        row = by_no.get(int(h.get("horseNumber") or 0))
        if not row:
            continue
        h["abilityEvidence"] = {
            "rank": row["abilityRank"],
            "score": row["abilityScore"],
            "scoreMeaning": "field-relative four-pillar head-to-head dominance; not win probability",
            "wins": row["evidenceWins"],
            "weak": row["evidenceWeak"],
            "sample": row["sample"],
            "components": row["components"],
            "pillarRanks": row["pillarRanks"],
            "evidenceCounts": row["evidenceCounts"],
            "supportTieBreakWins": row["supportTieBreakWins"],
            "modelVersion": row["modelVersion"],
        }
    detail["abilityRanking"] = [
        {
            "horseNumber": int(r["horse"].get("horseNumber") or 0),
            "name": r["horse"].get("name") or "",
            "rank": r["abilityRank"],
            "score": r["abilityScore"],
            "scoreMeaning": "field-relative four-pillar head-to-head dominance; not win probability",
            "sample": r["sample"],
            "evidenceWins": r["evidenceWins"],
            "evidenceWeak": r["evidenceWeak"],
            "components": r["components"],
            "pillarRanks": r["pillarRanks"],
            "evidenceCounts": r["evidenceCounts"],
            "supportTieBreakWins": r["supportTieBreakWins"],
            "modelVersion": r["modelVersion"],
        }
        for r in ranked
    ]
    detail["abilityRankingModelVersion"] = MODEL_VERSION
    return detail
