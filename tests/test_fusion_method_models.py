"""Chronological public-method emulation tests (never actual tipster picks)."""
from copy import deepcopy
from datetime import date, timedelta
import pytest

from arvexq.prediction.fusion_method_models import (
    METHODS, fit_observed_methods, predict_observed_methods, observed_buckets,
)
import json

OFF = "2026-10-24T12:00:00+09:00"
CAPTURE = "2026-10-24T10:00:00+09:00"


def race(day="2026-10-24", *, result=False, circuit="地方"):
    race_id = ("nar" if circuit == "地方" else "jra") + "-" + day + "-園田-01"
    details = {
        "id": race_id, "date": day, "circuit": circuit,
        "track": "園田", "surface": "ダート", "distance": 1400,
        "startTime": "12:00", "analysisMode": "平地",
        "horses": [
            {"horseNumber": no, "name": "馬" + str(no),
             "recentRaces": [
                 {"date": "2026-08-01", "finish": no,
                  "fieldSize": 5, "distance": 1400, "track": "園田",
                  "surface": "ダート", "cornerPositions": [no,no],
                  "opponentLevel": 2, "marginSeconds": .2 * no}]}
            for no in range(1, 6)],
    }
    if result:
        details["result"] = {
            "status": "確定", "finishers": [
                {"horseNumber": no, "finish": no} for no in range(1,6)],
            "payouts": [{"type":"単勝", "combination":"1", "amount":350}],
        }
    return details


def data():
    return [race((date(2026,9,1)+timedelta(days=i)).isoformat(),result=True)
            for i in range(30)]


def test_three_distinct_prior_trained_method_predictions_are_normalized_and_unmodified():
    models = fit_observed_methods(data(), circuit="地方", target_date="2026-10-24")
    assert set(models) == set(METHODS)
    assert len({m["modelVersion"] for m in models.values()}) == 3
    current = race()
    saved = deepcopy(current)
    preds = predict_observed_methods(
        current, models, captured_at=CAPTURE, scheduled_off_at=OFF)
    assert current == saved
    assert set(preds) == set(METHODS)
    for name, prediction in preds.items():
        assert prediction["notOriginalTipsterForecast"] is True
        assert prediction["modelVersion"] == models[name]["modelVersion"]
        assert len(prediction["trifecta"]) == 5*4*3
        assert sum(prediction["win"].values()) == pytest.approx(1)
        assert sum(prediction["top3"].values()) == pytest.approx(3)
        assert sum(row["probability"] for row in prediction["trifecta"]) == pytest.approx(1)
    assert preds["mineta"]["win"][1] > preds["mineta"]["win"][5]


def test_incomplete_or_future_training_cannot_generate_preoff_marks():
    records = data()
    with pytest.raises(ValueError, match="30 earlier"):
        fit_observed_methods(records[:29], circuit="地方", target_date="2026-10-24")
    models = fit_observed_methods(records, circuit="地方", target_date="2026-10-24")
    with pytest.raises(ValueError, match="scheduled off"):
        predict_observed_methods(race(), models,
                                 captured_at="2026-10-24T12:01:00+09:00",
                                 scheduled_off_at=OFF)
    with pytest.raises(ValueError, match="cross-circuit"):
        predict_observed_methods(race(circuit="中央"), models,
                                 captured_at=CAPTURE, scheduled_off_at=OFF)
    with pytest.raises(ValueError, match="target outcome"):
        predict_observed_methods(race(result=True), models,
                                 captured_at=CAPTURE, scheduled_off_at=OFF)


def test_future_result_only_comes_from_validation_not_as_a_feature():
    future = race("2026-10-24",result=True)
    # A future race may never be considered for an earlier calibration date.
    earlier = data()
    earlier.append(future)
    models = fit_observed_methods(earlier, circuit="地方", target_date="2026-10-24")
    assert all(m["trainingThrough"] == "2026-09-30" for m in models.values())
    assert all(len(m["trainingRaceIds"]) == 30 for m in models.values())


def test_reviewed_prior_video_is_a_fusion_feature_but_provisional_video_is_unknown():
    current = race()
    current["horses"][0]["visionResearchHistory"] = [{
        "raceId": "nar-2026-08-01-園田-01", "raceDate": "2026-08-01",
        "researchOnly": True, "identitySource": "externally-reviewed",
        "trackingCoverage": .95, "possibleSlowdownEvents": 1,
        "distanceLossMeters": 12.0,
    }]
    bucket = json.loads(observed_buckets(current)["expert:form"][1])
    assert bucket["videoStatus"] == "verified"
    assert bucket["videoSlowdown"] is True
    assert bucket["videoDistanceLoss"] is True
    current["horses"][0]["visionResearchHistory"][0]["identitySource"] = "automated-ocr-provisional"
    unknown = json.loads(observed_buckets(current)["expert:form"][1])
    assert unknown["videoStatus"] == "unknown"
