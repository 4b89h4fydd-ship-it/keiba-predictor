"""Regression tests for independent official NAR conditions and scratch parser."""
from arvexq.ingest.nar_environment_parser import _parse_nar_environment_html

def test_parse_weather_going_and_scratched_horse():
    html = '<html><body><div>天候：小雨　馬場状態：稍重</div><table><tr><th>3</th><td>7</td><td>出走取消</td></tr></table></body></html>'
    result = _parse_nar_environment_html(html)
    assert result["weather"] == "小雨"
    assert result["condition"] == "稍重"
    assert result["scratchMap"] == {7:"出走取消"}

def test_empty_html_has_no_observed_environment():
    assert _parse_nar_environment_html("") == {}
