"""126: Public data projection cannot promote old archives into active predictions.

Stored evidence is never mutated. This projection applies at delivery boundaries,
including nested additive API views and saved revision payloads.
"""
from copy import deepcopy
RETIRED_KEYS = frozenset(('aiEvaluation', 'integratedEvaluation', 'factorRanking', 'honmeiDecision',
    'preRacePrediction', 'preRaceBet', 'predictionAudit', 'frozenPredictionAudit',
    'winnerLearningProfile', 'betRecommendations', 'recommendedBets', 'tickets', 'buyList', 'bets',
    'markMethod', 'markEngineVersion', 'predictionModelVersion', 'mark', 'predMark', '印',
    'honmeiRole', 'modelProbabilities', 'forecastRevisions', 'currentForecastRevisionId',
    'predictionMarks', 'predictionEvidence', 'predictionRunnerCount', 'recommendedBetsStatus',
    'postRaceReference', 'postraceReferenceArchive', 'morningMarkSnapshot', 'officialMarkRevisions', 'modelMarkRevisions', 'savedForecastRevision',
    '_savedPreoffOriginal', 'legacyPredictionAudit', 'preRaceAudit', 'observedModelCoverage'))

def public_race(detail):
    """JSON race mapping -> detached facts; recursively remove retired outputs."""
    def project(value):
        if isinstance(value, dict):
            return {k: project(v) for k, v in value.items() if k not in RETIRED_KEYS}
        if isinstance(value, list): return [project(v) for v in value]
        return deepcopy(value)
    if not isinstance(detail, dict): return detail
    result = project(detail)
    # Stage64 trial was explicitly authorized. Continue to remove all retired
    # model keys, while retaining ONLY the current race's pre-off research
    # six-stage evidence in the already-existing researchShadow container.
    original_shadow = detail.get("researchShadow")
    trial = original_shadow.get("stage64") if isinstance(original_shadow, dict) else None
    authorized = False
    if isinstance(trial, dict) and trial.get("raceId") == detail.get("id") and trial.get("date") == detail.get("date"):
        from datetime import datetime
        from arvexq.prediction.prerace_archive import JST, post_at
        off = post_at(detail)
        owner = "jra" if detail.get("circuit") in ("中央", "jra") else (
            "nar" if detail.get("circuit") in ("地方", "nar") else None)
        stages = trial.get("stages")
        authorized = bool(
            off and datetime.now(JST) < off and owner
            and trial.get("circuit") == owner
            and trial.get("modelVersion") == owner + "-flat-shadow-v1"
            and isinstance(stages, dict)
            and all(isinstance(stages.get(key), dict) and stages[key].get("value") is not None
                    for key in ("ability", "runningStyle", "pace", "probability", "marks", "tickets"))
            and not detail.get("result", {}).get("finishers") if isinstance(detail.get("result"), dict) else True
        )
    if authorized:
        projected_shadow = dict(result.get("researchShadow") or {})
        projected_shadow["stage64"] = deepcopy(trial)
        result["researchShadow"] = projected_shadow
        result["predictionStatus"] = "research-provisional"
    else:
        result["predictionStatus"] = "disabled"
    return result
