"""Enrich already-computed racing forecasts with read-only evidence.

This must execute AFTER prediction computation. Evidence annotations never
replace pre-race marks, dynamic odds, seals, or the frozen morning race list.
"""
from __future__ import annotations
from typing import Any

from arvexq.prediction.sectional_profile import profile
from arvexq.prediction.bias_provenance import provenance
from arvexq.prediction.special_races import build_special_race_box


def career_coverage(horse: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    """Compact, read-only acquisition/completeness state shared with the UI."""
    from arvexq.career_missing import build_career_analysis
    a = build_career_analysis(horse, detail)
    ev = a.get("acquisition_evidence") or {}
    return {
        "version": "arvexq-career-coverage-ui-v1",
        "state": a.get("career_state"), "acquisition": a.get("acquisition_status"),
        "fields": a.get("field_completeness"), "dataLimitation": a.get("data_limitation"),
        "eligibleRuns": a.get("eligible_dated_runs"), "analyzedRuns": a.get("analyzed_runs"),
        "reportedStarts": ev.get("reportedStarts"), "reportedStartsSource": ev.get("reportedStartsSource"),
        "reason": ev.get("reason"), "missingFields": a.get("missing_fields") or [],
        "unusableRecords": a.get("unusable_dated_records"),
    }


def attach_evidence(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return detail
    detail["biasProvenance"] = provenance(detail)
    count = 0
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        if not horse.get("horseNumber"):
            continue
        try:
            horse["careerCoverage"] = career_coverage(horse, detail)
        except Exception as exc:  # evidence decoration must never block delivery
            horse["careerCoverage"] = {"version": "arvexq-career-coverage-ui-v1", "state": "acquisition-unverified",
                                       "acquisition": "unverified", "reason": f"coverage-error:{type(exc).__name__}"}
        from arvexq.prediction.observed_model import model_version
        evidence = (horse.get("integratedEvaluation") or {}).get("narModelEvidence") or {}
        horse["researchEvidence"] = {
            "factors": {
                "version": model_version(detail),
                "items": [
                    {"key": "mineta", "weight": .60, "value": evidence.get("mineta"),
                     "available": evidence.get("mineta") is not None},
                    {"key": "margin", "weight": .40, "value": evidence.get("margin"),
                     "available": evidence.get("margin") is not None}
                ],
                "calibrated": False,
                "note": "Observed 60/40 relative model scores are not verified hit probabilities.",
            },
            "sectionals": profile(horse, detail),
            "status": "jra-observed-official-proofs" if str(detail.get("circuit") or "") in ("中央", "JRA", "central") else "nar-observed-only",
        }
        count += 1
    detail["researchEvidenceVersion"] = "arvexq-race-intelligence-v1"
    detail["researchEvidenceHorses"] = count
    # An evidence-only namespace for the two JRA specialist populations.
    # No existing marks, ticket choices, or prediction inputs are rewritten.
    specialist = build_special_race_box(detail)
    if specialist is not None:
        detail["specialRaceBox"] = specialist
    return detail
