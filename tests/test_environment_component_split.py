"""Component contracts: 3 NAR and 4 JRA weather/going/scratch responsibilities."""
from bs4 import BeautifulSoup
from arvexq.ingest.nar_weather import parse_nar_weather
from arvexq.ingest.nar_going import parse_nar_going
from arvexq.ingest.nar_scratches import parse_nar_scratches
from arvexq.ingest.jra_weather import parse_jra_weather
from arvexq.ingest.jra_turf_going import parse_jra_turf_going
from arvexq.ingest.jra_dirt_going import parse_jra_dirt_going
from arvexq.ingest.jra_obstacle_going import parse_jra_obstacle_going
from arvexq.ingest.nar_environment_parser import _parse_nar_environment_html
from arvexq.ingest.jra_environment_parser import _parse_jra_environment_html

def test_nar_weather_is_independent():
    assert parse_nar_weather("天候：小雨　馬場状態：重") == "小雨"
    assert parse_nar_weather("馬場状態：重") is None

def test_nar_going_is_independent():
    assert parse_nar_going("馬場状態：不良　天候：晴") == "不良"
    assert parse_nar_going("天候：晴") is None

def test_nar_scratch_is_independent():
    html = "<table><tr><th>2</th><td>7</td><td>競走除外</td></tr><tr><th>3</th><td>8</td><td>出走</td></tr></table>"
    assert parse_nar_scratches(BeautifulSoup(html, "html.parser")) == {7:"除外"}
    assert parse_nar_scratches(BeautifulSoup("<div>天候：晴</div>", "html.parser")) == {}

def test_jra_weather_is_independent():
    assert parse_jra_weather("天候：小雪　芝：良") == "小雪"
    assert parse_jra_weather("芝：良") is None

def test_jra_turf_going_is_independent():
    assert parse_jra_turf_going("芝：稍重 ダート：不良") == "稍重"
    assert parse_jra_turf_going("ダート：不良") is None

def test_jra_dirt_going_is_independent():
    assert parse_jra_dirt_going("芝：良 ダート：重") == "重"
    assert parse_jra_dirt_going("芝：良") is None

def test_jra_obstacle_going_is_independent():
    assert parse_jra_obstacle_going({"芝":"稍重","ダート":"重"}) == "稍重"
    assert parse_jra_obstacle_going({"ダート":"重"}) == "重"
    assert parse_jra_obstacle_going({}) is None

def test_nar_parser_preserves_existing_output_contract():
    html = "<div>天候：小雨　馬場状態：稍重</div><table><tr><th>3</th><td>7</td><td>出走取消</td></tr></table>"
    assert _parse_nar_environment_html(html) == {
        "scratchMap":{7:"出走取消"},"weather":"小雨","condition":"稍重"
    }
    assert _parse_nar_environment_html("") == {}

def test_jra_parser_preserves_existing_output_contract():
    html = "<div>天候：晴　芝：良　ダート：稍重</div>"
    assert _parse_jra_environment_html(html,"ダート") == {
        "surfaceConditions":{"芝":"良","ダート":"稍重"},
        "weather":"晴","condition":"稍重"
    }
    assert _parse_jra_environment_html(html,"障害")["condition"] == "良"
    assert _parse_jra_environment_html("ダート：重","障害")["condition"] == "重"
    assert _parse_jra_environment_html("") == {}
