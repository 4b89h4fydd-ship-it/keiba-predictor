"""Publish only new calibrated predictions; never disclose internal video data.

Older saved model outputs remain as immutable D1 records but do not become
live predictions or public predictions after the old scorer is retired.
"""
from copy import deepcopy
from .engine import build_prediction
from .marks import generate_marks
from .tickets import generate_tickets

PRIVATE_OR_RETIRED = frozenset((
    "_internalVideoFeatures", "_internalThreeWayOdds", "videoTracks",
    "aiEvaluation", "integratedEvaluation", "factorRanking", "honmeiDecision",
    "preRacePrediction", "preRaceBet", "predictionAudit", "frozenPredictionAudit",
    "winnerLearningProfile", "betRecommendations", "recommendedBets", "tickets",
    "buyList", "bets", "markMethod", "markEngineVersion", "predictionModelVersion",
    "mark", "predMark", "印", "honmeiRole", "modelProbabilities",
    "forecastRevisions", "currentForecastRevisionId", "predictionMarks",
    "predictionEvidence", "predictionRunnerCount", "recommendedBetsStatus",
    "postRaceReference", "postraceReferenceArchive", "morningMarkSnapshot",
    "officialMarkRevisions", "modelMarkRevisions", "savedForecastRevision",
    "_savedPreoffOriginal", "legacyPredictionAudit", "preRaceAudit",
    "observedModelCoverage", "prediction", "forecastText"
))

def public_race(detail):
    def project(value):
        if isinstance(value, dict):
            return {k: project(v) for k,v in value.items() if k not in PRIVATE_OR_RETIRED}
        if isinstance(value, list):
            return [project(v) for v in value]
        return deepcopy(value)
    if not isinstance(detail,dict):
        return detail
    result=project(detail)
    forecast=build_prediction(detail)
    if forecast is None:
        result["predictionStatus"]="disabled"
        return result
    marks=generate_marks(forecast)
    result["predictionStatus"]="ready"
    result["predictionModelVersion"]=forecast["modelVersion"]
    result["prediction"]={
        k:deepcopy(v) for k,v in forecast.items()
        if k not in ("videoAnalyzedInternally",)
    }
    result["predictionMarks"]=marks
    result["recommendedBets"]=generate_tickets(forecast, marks)
    result["forecastText"]=forecast.get("forecastText","")
    by_number={x["horseNumber"]:x["mark"] for x in marks}
    for horse in result.get("horses") or []:
        if isinstance(horse,dict) and horse.get("horseNumber") in by_number:
            horse["predMark"]=by_number[horse["horseNumber"]]
    return result
