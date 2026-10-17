"""Retired prediction module. Keep import-compatible API without any scoring or marks."""
from __future__ import annotations

NAR_MODEL_VERSION = "arvexq-prediction-removed"
JRA_MODEL_VERSION = "arvexq-prediction-removed"
MODEL_VERSION = "arvexq-prediction-removed"

def model_version(race):
    return MODEL_VERSION

def rank_observed(horses, race):
    return []

def rank_nar(horses, race):
    return []

def rank_jra(horses, race):
    return []

def apply_observed_marks(detail):
    if not isinstance(detail, dict):
        return detail
    for horse in detail.get("horses", []) or []:
        if isinstance(horse, dict):
            horse.pop("integratedEvaluation", None)
            horse.pop("mark", None)
    for key in ("factorRanking", "honmeiDecision", "markMethod", "observedModelCoverage"):
        detail.pop(key, None)
    detail["predictionStatus"] = "disabled"
    detail["predictionModelVersion"] = MODEL_VERSION
    detail["markEngineVersion"] = MODEL_VERSION
    return detail

def apply_nar_marks(detail):
    return apply_observed_marks(detail)
