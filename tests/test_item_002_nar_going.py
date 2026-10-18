from arvexq.ingest.nar_environment_parser import _parse_nar_environment_html
from arvexq.ingest.nar_going import parse_nar_going, parse_nar_going_moisture


def test_flat_nar_going_remains_independent():
    assert parse_nar_going("馬場状態：稍重　天候：晴") == "稍重"
    assert parse_nar_going_moisture("馬場状態：稍重") is None


def test_banei_moisture_is_observed_separately():
    assert parse_nar_going("馬場：1.0　天候：晴") is None
    assert parse_nar_going_moisture("馬場：1.0　天候：晴") == "1.0"


def test_banei_composition_preserves_weather_and_moisture():
    assert _parse_nar_environment_html("<div>天候：晴　馬場：1.0</div>") == {
        "scratchMap": {}, "weather": "晴", "goingMoisture": "1.0"
    }
