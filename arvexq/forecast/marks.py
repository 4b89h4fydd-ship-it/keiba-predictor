"""Project marks computed by the calibrated three-analysis model (no rescoring)."""
from copy import deepcopy

def generate_marks(prediction):
    if not isinstance(prediction,dict) or prediction.get("predictionStatus")!="ready":
        return []
    return deepcopy(prediction.get("marks") or [])

def clear_marks(detail):
    if not isinstance(detail,dict):
        return detail
    for horse in detail.get("horses") or []:
        if isinstance(horse,dict):
            for key in ("integratedEvaluation","mark","predMark","honmeiRole","modelProbabilities"):
                horse.pop(key,None)
    for key in ("factorRanking","honmeiDecision","markMethod","observedModelCoverage"):
        detail.pop(key,None)
    return detail
