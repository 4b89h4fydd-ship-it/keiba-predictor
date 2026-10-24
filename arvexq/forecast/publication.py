"""126: Public data projection cannot promote old archives into active predictions.

Stored evidence is never mutated. This projection applies at delivery boundaries,
including nested additive API views and saved revision payloads.
"""
from copy import deepcopy
from .engine import build_prediction
from .marks import generate_marks
from .tickets import generate_tickets
from arvexq.prediction.empirical_fusion import VERSION as FUSION_VERSION
RETIRED_KEYS = frozenset(('aiEvaluation', 'integratedEvaluation', 'factorRanking', 'honmeiDecision',
    'preRacePrediction', 'preRaceBet', 'fusionInputs', 'predictionAudit', 'frozenPredictionAudit',
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
        # A stored, verified original remains immutable historical race evidence.
        # Publishing its original marks/tickets after the off is NOT a new
        # prediction. Never create a product retroactively for an empty row.
        original = detail.get('prediction')
        original_marks = detail.get('predictionMarks')
        original_tickets = detail.get('recommendedBets')
        labels = ('◎', '○', '▲', '△', '☆')
        roster = {h.get('horseNumber') for h in detail.get('horses') or []
                  if isinstance(h, dict)}
        valid = (isinstance(original, dict)
                 and detail.get('predictionStatus') == 'ready'
                 and detail.get('predictionModelVersion') in (FUSION_VERSION, 'arvexq-stage64-product-v1')
                 and original.get('modelVersion') == detail.get('predictionModelVersion')
                 and original.get('predictionStatus') == 'ready'
                 and original.get('productionEligible') is True
                 and original.get('raceId') == detail.get('id')
                 and original.get('date') == detail.get('date')
                 and isinstance(original_marks, list) and len(original_marks) == 5
                 and isinstance(original_tickets, list)
                 and all(isinstance(m, dict) and m.get('mark') == labels[i]
                         and type(m.get('horseNumber')) is int
                         and m['horseNumber'] in roster
                         for i, m in enumerate(original_marks))
                 and len({m['horseNumber'] for m in original_marks}) == 5)
        if valid:
            result['predictionStatus'] = 'ready'
            result['predictionModelVersion'] = original['modelVersion']
            result['prediction'] = deepcopy(original)
            if isinstance(original.get('forecastText'), str):
                result['forecastText'] = original['forecastText']
            result['predictionMarks'] = deepcopy(original_marks)
            # The original, pre-off recorded picks stay untouched after the off.
            # Never generate or reorder tickets using post-off odds/outcomes.
            result['recommendedBets'] = deepcopy(original_tickets)
            by_no = {m['horseNumber']: m['mark'] for m in original_marks}
            for horse in result.get('horses') or []:
                if horse.get('horseNumber') in by_no:
                    horse['predMark'] = by_no[horse['horseNumber']]
            return result
        result['predictionStatus'] = 'disabled'
        return result
    marks = generate_marks(prediction)
    result['predictionStatus'] = 'ready'
    result['predictionModelVersion'] = prediction['modelVersion']
    result['prediction'] = prediction
    result['forecastText'] = prediction.get('forecastText', '')
    result['predictionMarks'] = marks
    result['recommendedBets'] = generate_tickets(prediction, marks, race=detail)
    by_no = {row['horseNumber']: row['mark'] for row in marks}
    for horse in result.get('horses') or []:
        no = horse.get('horseNumber')
        if no in by_no:
            horse['predMark'] = by_no[no]
    return result
