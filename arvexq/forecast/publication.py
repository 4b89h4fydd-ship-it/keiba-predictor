"""126: Public data projection cannot promote old archives into active predictions.

Stored evidence is never mutated. This projection applies at delivery boundaries,
including nested additive API views and saved revision payloads.
"""
from copy import deepcopy
from .engine import VERSION, build_prediction
from .inputs import prediction_input
from .marks import generate_marks

RETIRED_KEYS = frozenset(('aiEvaluation', 'integratedEvaluation', 'factorRanking', 'honmeiDecision',
    'preRacePrediction', 'preRaceBet', 'predictionAudit', 'frozenPredictionAudit',
    'winnerLearningProfile', 'betRecommendations', 'recommendedBets', 'tickets', 'buyList', 'bets',
    'markMethod', 'markEngineVersion', 'predictionModelVersion', 'mark', 'predMark', '印',
    'honmeiRole', 'modelProbabilities', 'forecastRevisions', 'currentForecastRevisionId',
    'morningMarkSnapshot', 'officialMarkRevisions', 'modelMarkRevisions', 'savedForecastRevision',
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
    prediction = build_prediction(prediction_input(result))
    if prediction is None:
        result['predictionStatus'] = 'disabled'
    else:
        result['predictionStatus'] = 'provisional'
        result['predictionEvidence'] = prediction['evidence']
        result['predictionRunnerCount'] = prediction['runnerCount']
        result['predictionMarks'] = generate_marks(prediction)
        result['recommendedBetsStatus'] = 'not_evaluated_without_verified_odds'
        # Keep joint scenarios internal; avoid publishing large probabilistic blobs.
    result['predictionModelVersion'] = VERSION
    return result
