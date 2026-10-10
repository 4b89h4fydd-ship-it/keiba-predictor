"""Enrich already-computed racing forecasts with read-only evidence.

This must execute AFTER prediction computation. Evidence annotations never
replace pre-race marks, dynamic odds, seals, or the frozen morning race list.
"""
from __future__ import annotations
from typing import Any

from arvexq.prediction.factor_cards import evidence_card
from arvexq.prediction.sectional_profile import profile
from arvexq.prediction.bias_provenance import provenance


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
        horse["researchEvidence"] = {
            "factors": evidence_card(horse, detail),
            "sectionals": profile(horse, detail),
            "status": "read-only-unverified-predictive-lift",
        }
        count += 1
    detail["researchEvidenceVersion"] = "arvexq-race-intelligence-v1"
    detail["researchEvidenceHorses"] = count
    return detail
