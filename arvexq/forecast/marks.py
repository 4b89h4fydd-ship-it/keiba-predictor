"""Sanitize historical mark fields without generating new model marks."""

def clear_marks(detail):
    if not isinstance(detail, dict):
        return detail
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        for key in ("integratedEvaluation", "mark", "predMark", "honmeiRole", "modelProbabilities"):
            horse.pop(key, None)
    for key in ("factorRanking", "honmeiDecision", "markMethod", "observedModelCoverage"):
        detail.pop(key, None)
    return detail
