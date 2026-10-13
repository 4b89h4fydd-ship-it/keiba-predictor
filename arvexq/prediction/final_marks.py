from __future__ import annotations

from typing import Any
from arvexq.prediction.factor_model import MODEL_VERSION, PRIMARY_PILLARS, rank_factor_model
from arvexq.prediction.career_readiness import attach_career_readiness

MARK_ENGINE_VERSION = "arvexq-true-run-pure-sectional-marks-v1"
CORE_MARKS = ("◎", "○", "▲")
LOWER_MARKS = ("☆", "△", "注")

def sufficiently_observed_partial_career(
    detail: dict[str, Any], readiness: dict[str, Any]
) -> bool:
    """A high-coverage field may be forecast without calling ingestion complete.

    This is not a whole-career verification: it only permits an explicitly
    labelled pre-off provisional prediction if missing acquisition audits affect
    at most two runners, with several dated, usable runs for each.
    """
    from arvexq.prediction.past_performance import observed_runs

    if not isinstance(detail, dict) or detail.get("_entryOnly"):
        return False
    horses = [
        h for h in (detail.get("horses") or [])
        if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
        and not h.get("scratched") and not h.get("withdrawn")
        and not any(x in str(h.get("status") or "") for x in ("取消", "除外", "欠場"))
    ]
    total = len(horses)
    complete = int(readiness.get("completeHorses") or 0)
    blocked = readiness.get("blockedHorses") or []
    if total < 5 or total != int(readiness.get("activeHorses") or 0):
        return False
    # An observed, date-bounded history is usable evidence even when the
    # provider's lifetime start-count verification endpoint is unavailable.
    # This is NOT evidence of full career completeness. Require every active
    # horse to have five distinct, usable pre-race dated starts, and reject
    # contradictory counts or identity/cutoff errors.
    if complete < max(4, (4 * total + 4) // 5) or not 0 < len(blocked) <= 2:
        if len(blocked) != total:
            return False
        by_no = {int(h["horseNumber"]): h for h in horses}
        acceptable = {"provider-fetch-failed", "reported-starts-unknown"}
        for entry in blocked:
            horse = by_no.get(int(entry.get("horseNumber") or 0))
            if (not horse or not str(horse.get("name") or "").strip()
                    or entry.get("reason") not in acceptable
                    or entry.get("reportedStarts") is not None):
                return False
            try:
                runs = observed_runs(horse, detail, limit=None)
            except (ValueError, TypeError, KeyError):
                return False
            if len({str(run.get("date") or "") for run in runs}) < 5:
                return False
        return True
    by_no = {int(h["horseNumber"]): h for h in horses}
    for entry in blocked:
        horse = by_no.get(int(entry.get("horseNumber") or 0))
        if not horse or not str(horse.get("name") or "").strip():
            return False
        try:
            runs = observed_runs(horse, detail, limit=None)
        except (ValueError, TypeError, KeyError):
            return False
        if len(runs) < 3:
            return False
    return True



def apply_core_marks(detail: dict[str, Any]) -> dict[str, Any]:
    """One marks authority; old four-pillar and podium-axis paths deleted."""
    if not isinstance(detail, dict):
        return detail
    attach_career_readiness(detail)
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    readiness = detail.get("careerReadiness") or {}
    full = readiness.get("ready") is True
    limited = not full and sufficiently_observed_partial_career(detail, readiness)
    if not full and not limited:
        for h in horses:
            e = h.get("integratedEvaluation")
            if isinstance(e, dict):
                e["mark"] = ""
                e.pop("rank", None)
        detail.pop("factorRanking", None)
        detail.pop("honmeiDecision", None)
        detail.pop("multiHeadSummary", None)
        detail["predictionStatus"] = "waiting-for-full-career"
        return detail
    detail["predictionStatus"] = "partial-career-evidence" if limited else "ready"
    if limited:
        readiness["predictionEligible"] = True
        readiness["predictionEvidencePolicy"] = (
            "all-active-five-dated-observed-total-unverified-v2"
            if int(readiness.get("completeHorses") or 0) == 0
            else "80pct-verified-max2-unverified-min3-observed-v1"
        )
    ranked = rank_factor_model(horses, detail)
    for horse in horses:
        e = horse.setdefault("integratedEvaluation", {})
        e["mark"] = ""
        e["markEngineVersion"] = MARK_ENGINE_VERSION
        e["markSource"] = "true-run-pure-sectional-45-35-20"
        for old in ("multiHead", "strengthHeadRank", "winHeadRank", "upsideHeadRank",
                    "upsideCandidate", "dangerPopular", "podiumAxisScore"):
            e.pop(old, None)
    detail.pop("multiHeadSummary", None)
    if not ranked:
        detail["predictionStatus"] = "insufficient-three-factor-evidence"
        detail.pop("factorRanking", None)
        detail.pop("honmeiDecision", None)
        return detail
    detail["factorRanking"] = []
    leader = ranked[0]
    gap = leader["score"] - ranked[1]["score"] if len(ranked) > 1 else 0.
    complete = leader["primaryPillarCoverage"] == 3
    grade = ("A" if complete and leader["score"] >= .80 and gap >= .04 and leader["sample"] >= 3
             else "B" if leader["primaryPillarCoverage"] >= 2 and leader["score"] >= .65
             else "C")
    axis = leader["horse"]
    axis_no = int(axis.get("horseNumber") or 0)
    detail["honmeiDecision"] = {
        "version": MARK_ENGINE_VERSION, "eligible": grade == "A",
        "horseNumber": axis_no, "displayHonmei": True, "confidenceGrade": grade,
        "role": "win", "fixedAxisAllowed": grade == "A", "axisScore": round(leader["score"], 6),
        "axisMargin": round(gap, 6), "axisMeaning": "relative-three-factor-score-not-probability",
        "reason": "three-factor-confidence" if grade == "A" else "relative-honmei-not-fixed",
        "axisCandidates": [
            {"horseNumber": int(z["horse"].get("horseNumber") or 0),
             "score": round(z["score"], 6), "coverage": z["primaryPillarCoverage"]}
            for z in ranked[:5]
        ]
    }
    for row in ranked:
        h = row["horse"]
        e = h.setdefault("integratedEvaluation", {})
        evidence = {
            "rank": row["rank"], "dominanceScore": row["dominanceScore"],
            "scoreMeaning": "TRUE RUN 45 + PURE 35 + SECTIONAL 20, not probability",
            "pillarScores": row["pillarScores"], "pillarRanks": row["pillarRanks"],
            "evidenceCounts": row["evidenceCounts"],
            "evidenceFamilyCounts": row["evidenceFamilyCounts"],
            "primaryPillarCoverage": row["primaryPillarCoverage"],
            "rawMetrics": row["raw"], "sample": row["sample"],
            "modelVersion": MODEL_VERSION,
        }
        e["coreAbilityRank"] = row["rank"]
        e["coreAbilityScore"] = row["dominanceScore"]
        e["primaryPillars"] = list(PRIMARY_PILLARS)
        e["factorEvidence"] = evidence
        e["pastPerformance"] = row["pastPerformance"]
        e["careerProfile"] = row["careerProfile"]
        e["honmeiEligible"] = bool(grade == "A" and h is axis)
        e["honmeiRole"] = "win" if h is axis else ""
        e["honmeiGrade"] = grade if h is axis else ""
        e["honmeiGateVersion"] = MARK_ENGINE_VERSION
        h["abilityEvidence"] = evidence
        detail["factorRanking"].append({
            "horseNumber": int(h.get("horseNumber") or 0),
            "name": h.get("name") or "", **evidence,
        })
    # One ranking owns all marks. 注 is reserved and never a forced sixth rank.
    for row, mark in zip(ranked, ("◎", "○", "▲", "△", "☆")):
        row["horse"]["integratedEvaluation"]["mark"] = mark
    for row in ranked:
        row["horse"]["integratedEvaluation"]["rank"] = row["rank"]
    detail["markEngineVersion"] = MARK_ENGINE_VERSION
    detail["predictionModelVersion"] = MODEL_VERSION
    detail["markMethod"] = "TRUE RUN45%＋PURE35%＋SECTIONAL20%; unified marks and betting"
    return detail
