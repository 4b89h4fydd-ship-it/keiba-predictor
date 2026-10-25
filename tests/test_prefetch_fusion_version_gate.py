"""D1 prefetch must not publish retired engine output as a new forecast."""
from unittest.mock import patch

from arvexq.prediction.empirical_fusion import VERSION
from scripts.arvexq_prefetch import _attach_empirical_fusion_products


def test_retired_projection_is_not_attached():
    original = {"id": "nar-2026-10-26-園田-01", "horses": []}
    projected = {
        "predictionStatus": "ready",
        "predictionModelVersion": "retired-prediction-model",
        "prediction": {"modelVersion": "retired-prediction-model"},
        "predictionMarks": [], "recommendedBets": [],
    }
    with patch("arvexq.forecast.publication.public_race", return_value=projected):
        assert _attach_empirical_fusion_products(original) == original
    assert "prediction" not in original


def test_replacement_forecast_projection_is_attached_without_mutating_source():
    original = {"id": "nar-2026-10-26-園田-01", "horses": [
        {"horseNumber": 1, "name": "馬一"},
        {"horseNumber": 2, "name": "馬二"},
    ]}
    projected = {
        "predictionStatus": "ready", "predictionModelVersion": VERSION,
        "forecastText": "展開予想の検証コメント",
        "prediction": {"modelVersion": VERSION},
        "predictionMarks": [{"horseNumber": 1, "mark": "◎"}],
        "recommendedBets": [],
    }
    with patch("arvexq.forecast.publication.public_race", return_value=projected):
        result = _attach_empirical_fusion_products(original)
    assert result["predictionModelVersion"] == VERSION
    assert result["predictionMarks"] == projected["predictionMarks"]
    assert result["forecastText"] == "展開予想の検証コメント"
    assert result["horses"][0]["predMark"] == "◎"
    assert "predMark" not in result["horses"][1]
    assert "predMark" not in original["horses"][0]
    assert "prediction" not in original
