"""Research-only five-run reliability estimator, not used in live predictions."""
from arvexq.prediction.past_performance import observed_runs


def score(horse, race):
    runs = observed_runs(horse, race, limit=5)
    grades = [(run['fieldSize'] - run['finish']) / (run['fieldSize'] - 1) for run in runs]
    if not grades:
        return None
    weights = list(range(len(grades), 0, -1))
    recent = sum(w * grade for w, grade in zip(weights, grades)) / sum(weights)
    reliability = len(grades) / (len(grades) + 3)
    return 0.5 + reliability * (recent - 0.5)
