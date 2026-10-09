"""Enrich already-computed racing forecasts with read-only evidence.

This must execute AFTER prediction computation. Evidence annotations never
replace pre-race marks, dynamic odds, seals, or the frozen morning race list.
"""
from __future__ import annotations
from typing import Any

from arvexq.prediction.factor_cards import evidence_card
from arvexq.prediction.sectional_profile import profile
from arvexq.prediction.bias_provenance import provenance


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
        horse["researchEvidence"] = {
            "factors": evidence_card(horse, detail),
            "sectionals": profile(horse, detail),
            "status": "read-only-unverified-predictive-lift",
        }
        count += 1
    detail["researchEvidenceVersion"] = "arvexq-race-intelligence-v1"
    detail["researchEvidenceHorses"] = count
    return detail
