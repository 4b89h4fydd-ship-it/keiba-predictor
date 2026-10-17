from arvexq.ingest.horse_measurements import (
    _safe_body_weight_value, _safe_carried_weight_value, _sanitize_horse_measurements,
)

def test_horse_body_weight_bounds():
    assert _safe_body_weight_value("500kg") == 500
    assert _safe_body_weight_value(240) is None
    assert _safe_body_weight_value(810) is None

def test_carried_weight_does_not_confuse_body_weight():
    assert _safe_carried_weight_value("▲ 51.0", 500) == 51.0
    assert _safe_carried_weight_value("500", 500) is None

def test_horse_measurements_remain_independent_of_predictions():
    horse = {"bodyWeight": "498", "carriedWeight": "55.0",
             "recentRaces": [{"bodyWeight": "497", "carriedWeight": "54.0"}]}
    result = _sanitize_horse_measurements(horse)
    assert result["bodyWeight"] == 498
    assert result["recentRaces"][0]["bodyWeight"] == 497
    assert result["recentRaces"][0]["carriedWeight"] == 54.0
    assert horse["bodyWeight"] == "498"
