"""Synthetic contract checks, not racing performance evidence."""
from copy import deepcopy
from arvexq.forecast.engine import build_prediction
from tests.test_empirical_fusion_live_contract import fixture, NOW


def test_reviewed_video_never_claims_unconsumed_correction():
    facts = fixture()
    baseline = build_prediction(facts, now=NOW)
    facts["horses"][0]["visionResearchHistory"] = [{
        "researchOnly": True, "identitySource": "externally-reviewed",
        "trackingCoverage": 1.0,
    }]
    original = deepcopy(facts)
    output = build_prediction(facts, now=NOW)
    assert output is not None
    assert facts == original
    pace = output["paceEvidence"]
    assert pace["videoReviewCandidateRuns"] == 1
    assert pace["verifiedHistoricalVideoRuns"] == 0
    assert pace["videoAppliedToFusion"] is False
    assert pace["videoApplicationStatus"] == "not-applied-awaiting-validation"
    assert "映像補正は未適用・検証待ち" in output["forecastText"]
    assert "融合特徴量へ反映" not in output["forecastText"]
    assert output["predictionMarks"] == baseline["predictionMarks"]
    assert output["recommendedBets"] == baseline["recommendedBets"]
    assert output["stages"]["probability"] == baseline["stages"]["probability"]


def test_no_video_does_not_invent_measurements():
    output = build_prediction(fixture(), now=NOW)
    assert output["paceEvidence"]["videoReviewCandidateRuns"] == 0
    assert output["paceEvidence"]["videoAppliedToFusion"] is False
