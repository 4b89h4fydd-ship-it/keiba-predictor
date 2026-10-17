"""116: Production mark generation independent of prediction and bets."""

def generate_marks(prediction):
    """Prediction -> empty marks until a mark policy is explicitly approved."""
    return []


def clear_marks(detail):
    """Remove obsolete live mark values in place; keep raw race/history facts."""
    if not isinstance(detail, dict): return detail
    for horse in detail.get('horses') or []:
        if not isinstance(horse, dict): continue
        for key in ('integratedEvaluation', 'mark', 'predMark', 'honmeiRole', 'modelProbabilities'):
            horse.pop(key, None)
    for key in ('factorRanking', 'honmeiDecision', 'markMethod', 'observedModelCoverage'):
        detail.pop(key, None)
    return detail
