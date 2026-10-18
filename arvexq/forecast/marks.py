"""Approved baseline marks produced only from a real pre-off prediction."""

def generate_marks(prediction):
    if not isinstance(prediction, dict) or not prediction.get("scenarios"):
        return []
    from arvexq.prediction.recommendation_engine import rank_marks
    ranked = rank_marks(prediction["scenarios"], max_lows=3)
    marks = ranked["marks"]
    return [{"horseNumber": int(h), "mark": marks[h],
             "winProbability": round(ranked["win"].get(h, 0), 4),
             "top3Probability": round(ranked["top3"].get(h, 0), 4)}
            for h in sorted(marks, key=lambda k: int(k))]


def clear_marks(detail):
    """Remove obsolete live mark values; preserve raw race and history facts."""
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
