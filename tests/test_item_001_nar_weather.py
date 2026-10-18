"""Item 001 NAR weather parser: independent source-observation contracts."""
import pytest
from arvexq.ingest.nar_weather import parse_nar_weather
from arvexq.ingest.nar_environment_parser import _parse_nar_environment_html


@pytest.mark.parametrize("text,expected", [
    ("天候：晴", "晴"),
    ("天候:曇", "曇"),
    ("天候　小雨", "小雨"),
    ("天候：小雪", "小雪"),
    ("天候：雨", "雨"),
    ("天候：雪", "雪"),
    ("馬場状態：不良", None),
    ("取消　7号", None),
    ("", None),
    (None, None),
])
def test_observed_nar_weather_only(text, expected):
    assert parse_nar_weather(text) == expected


def test_nar_weather_absent_does_not_guess_from_going_or_scratches():
    result = _parse_nar_environment_html("<div>馬場状態：重</div>")
    assert "weather" not in result
    assert result["condition"] == "重"
    assert result["scratchMap"] == {}


def test_nar_weather_composed_without_mutating_other_fields():
    result = _parse_nar_environment_html(
        "<div>天候：雨　馬場状態：稍重</div>"
        "<table><tr><th>3</th><td>7</td><td>出走取消</td></tr></table>")
    assert result == {"weather": "雨", "condition": "稍重",
                      "scratchMap": {7: "出走取消"}}
