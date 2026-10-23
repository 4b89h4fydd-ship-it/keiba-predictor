"""126: Public data projection cannot promote old archives into active predictions.

Stored evidence is never mutated. This projection applies at delivery boundaries,
including nested additive API views and saved revision payloads.
"""
from copy import deepcopy
from .engine import build_prediction
from .marks import generate_marks
from .tickets import generate_tickets
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
    prediction = build_prediction(detail)
    if prediction is None:
        result['predictionStatus'] = 'disabled'
        return result
    marks = generate_marks(prediction)
    result['predictionStatus'] = 'ready'
    result['predictionModelVersion'] = prediction['modelVersion']
    result['prediction'] = prediction
    result['predictionMarks'] = marks
    result['recommendedBets'] = generate_tickets(prediction, marks)
    by_no = {row['horseNumber']: row['mark'] for row in marks}
    for horse in result.get('horses') or []:
        no = horse.get('horseNumber')
        if no in by_no:
            horse['predMark'] = by_no[no]
    return result
