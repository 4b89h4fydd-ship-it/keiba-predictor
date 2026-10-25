"""D1 prefetch must not publish retired engine output as a new forecast."""
from unittest.mock import patch

from arvexq.prediction.empirical_fusion import VERSION
from scripts.arvexq_prefetch import _attach_empirical_fusion_products


def test_retired_stage64_projection_is_not_attached():
    original = {"id": "nar-2026-10-26-園田-01", "horses": []}
    projected = {
        "predictionStatus": "ready",
        "predictionModelVersion": "arvexq-stage64-product-v1",
        "prediction": {"modelVersion": "arvexq-stage64-product-v1"},
        "predictionMarks": [], "recommendedBets": [],
    }
    with patch("arvexq.forecast.publication.public_race", return_value=projected):
        assert _attach_empirical_fusion_products(original) == original
    assert "prediction" not in original


def test_replacement_forecast_projection_is_attached_without_mutating_source():
    original = {"id": "nar-2026-10-26-園田-01", "horses": []}
    projected = {
        "predictionStatus": "ready", "predictionModelVersion": VERSION,
        "prediction": {"modelVersion": VERSION},
        "predictionMarks": [{"horseNumber": 1, "mark": "◎"}],
        "recommendedBets": [],
    }
    with patch("arvexq.forecast.publication.public_race", return_value=projected):
        result = _attach_empirical_fusion_products(original)
    assert result["predictionModelVersion"] == VERSION
    assert result["predictionMarks"] == projected["predictionMarks"]
    assert "prediction" not in original
