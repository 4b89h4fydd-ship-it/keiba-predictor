from __future__ import annotations

from statistics import median
from typing import Any

MODEL_VERSION = "arvexq-race-selectability-v1"
PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")


def _f(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _med(values: list[float | None]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return float(median(vals)) if vals else None


def build_race_selectability_features(detail: dict[str, Any]) -> dict[str, Any]:
    """Describe whether a race is predictable without deciding that it is selected.

    This deliberately emits evidence, not a hand-weighted confidence score. Future
    frozen outcomes can learn which combinations correspond to reliable races.
    Popularity/odds are excluded because race predictability and market value are
    separate decisions.
    """
    ranking = [r for r in (detail.get("factorRanking") or []) if isinstance(r, dict)]
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    if not ranking:
        return {
            "modelVersion": MODEL_VERSION,
            "available": False,
            "fieldSize": len(horses),
        }

    leader = ranking[0]
    leader_no = _i(leader.get("horseNumber"))
    mh = detail.get("multiHeadSummary") if isinstance(detail.get("multiHeadSummary"), dict) else {}
    mh_winner = _i(mh.get("winnerHorseNumber"))
    win_gap = _f(mh.get("winnerGap"))

    by_no = {_i(r.get("horseNumber")): r for r in ranking if _i(r.get("horseNumber")) > 0}
    leader_row = by_no.get(leader_no, leader)
    leader_mh = leader_row.get("multiHead") if isinstance(leader_row.get("multiHead"), dict) else {}
    strength_rank = _i(leader_mh.get("strengthRank"), 999)
    win_rank = _i(leader_mh.get("winRank"), 999)
    upside_rank = _i(leader_mh.get("upsideRank"), 999)
    fragility = _f(leader_mh.get("fragilityScore"))

    pillar_scores = leader_row.get("pillarScores") if isinstance(leader_row.get("pillarScores"), dict) else {}
    pillar_ranks = leader_row.get("pillarRanks") if isinstance(leader_row.get("pillarRanks"), dict) else {}
    family_counts = leader_row.get("evidenceFamilyCounts") if isinstance(leader_row.get("evidenceFamilyCounts"), dict) else {}
    evidence_counts = leader_row.get("evidenceCounts") if isinstance(leader_row.get("evidenceCounts"), dict) else {}

    primary_available = sum(pillar_scores.get(p) is not None for p in PRIMARY_PILLARS)
    primary_rank1 = sum(_i(pillar_ranks.get(p), 999) == 1 for p in PRIMARY_PILLARS)
    primary_family_count = sum(_i(family_counts.get(p)) for p in PRIMARY_PILLARS)
    primary_metric_count = sum(_i(evidence_counts.get(p)) for p in PRIMARY_PILLARS)

    core_strength_agree = strength_rank == 1
    core_win_agree = win_rank == 1
    core_multihead_agree = bool(mh_winner and mh_winner == leader_no)

    # Field-level evidence dispersion: not a confidence score, just an observed fact.
    top3 = ranking[:3]
    top3_family_counts = [
        sum(_i((r.get("evidenceFamilyCounts") or {}).get(p)) for p in PRIMARY_PILLARS)
        for r in top3
    ]

    completeness: list[float] = []
    context_coverage: list[float] = []
    for h in horses:
        ev = h.get("integratedEvaluation") if isinstance(h.get("integratedEvaluation"), dict) else {}
        dc = _f(ev.get("dataCompleteness"))
        if dc is not None:
            completeness.append(dc / 100.0 if dc > 1.5 else dc)
        ce = h.get("contextualEvidence") if isinstance(h.get("contextualEvidence"), dict) else {}
        cc = _f(ce.get("evidenceCoverage"))
        if cc is not None:
            context_coverage.append(cc)

    return {
        "modelVersion": MODEL_VERSION,
        "available": True,
        "fieldSize": len(horses),
        "leaderHorseNumber": leader_no,
        "multiHeadWinnerHorseNumber": mh_winner or None,
        "coreStrengthAgree": core_strength_agree,
        "coreWinAgree": core_win_agree,
        "coreMultiHeadAgree": core_multihead_agree,
        "allDecisionHeadsAgree": bool(core_strength_agree and core_win_agree and core_multihead_agree),
        "winnerGap": win_gap,
        "leaderFragility": fragility,
        "leaderPrimaryPillarAvailable": primary_available,
        "leaderPrimaryRank1Count": primary_rank1,
        "leaderPrimaryFamilyCount": primary_family_count,
        "leaderPrimaryMetricCount": primary_metric_count,
        "top3PrimaryFamilyCountMedian": _med([float(v) for v in top3_family_counts]),
        "fieldDataCompletenessMedian": _med(completeness),
        "fieldContextCoverageMedian": _med(context_coverage),
        "predictionModelVersion": detail.get("predictionModelVersion"),
        "markEngineVersion": detail.get("markEngineVersion"),
    }
