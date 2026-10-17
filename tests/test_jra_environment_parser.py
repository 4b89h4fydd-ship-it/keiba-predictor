from arvexq.ingest.jra_environment_parser import _parse_jra_environment_html

def test_jra_weather_and_both_surface_conditions():
    html='<html><body>天候：晴　芝：良　ダート：稍重</body></html>'
    r=_parse_jra_environment_html(html,"ダート")
    assert r["weather"]=="晴"
    assert r["condition"]=="稍重"
    assert r["surfaceConditions"]=={"芝":"良","ダート":"稍重"}

def test_jra_obstacle_uses_available_surface():
    assert _parse_jra_environment_html("芝：重","障害")["condition"]=="重"
