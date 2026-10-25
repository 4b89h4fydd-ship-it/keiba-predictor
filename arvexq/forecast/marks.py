"""Pre-off empirical fusion marks; no ranking is calculated in the UI."""

def generate_marks(prediction):
    from arvexq.prediction.empirical_fusion import VERSION as FUSION_VERSION
    if (not isinstance(prediction, dict) or prediction.get("modelVersion") != FUSION_VERSION
            or prediction.get("predictionStatus") != "ready"):
        return []
    stages = prediction.get("stages") or {}
    value = ((stages.get("marks") or {}).get("value") or {})
    order = value.get("orderedWinCandidates") or []
    win = ((stages.get("probability") or {}).get("value") or {}).get("win") or {}
    labels = ("◎", "○", "▲", "△", "☆")
    return [{"horseNumber": int(no), "mark": labels[i], "winProbability": win.get(no)}
            for i, no in enumerate(order[:5])]

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
