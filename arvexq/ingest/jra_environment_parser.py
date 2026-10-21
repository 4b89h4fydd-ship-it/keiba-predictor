"""Compose independent JRA weather, turf, dirt and obstacle-going extractors."""
from bs4 import BeautifulSoup
from arvexq.components.item_004.jra_weather import parse_jra_weather
from arvexq.components.item_005.jra_turf_going import parse_jra_turf_going
from arvexq.components.item_006.jra_dirt_going import parse_jra_dirt_going
from arvexq.components.item_007.jra_obstacle_going import parse_jra_obstacle_going

def _parse_jra_environment_html(html: str, surface: str = "") -> dict:
    if not html:
        return {}
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    result = {"surfaceConditions": {}}
    weather = parse_jra_weather(text)
    if weather is not None:
        result["weather"] = weather
    turf = parse_jra_turf_going(text)
    dirt = parse_jra_dirt_going(text)
    if turf is not None:
        result["surfaceConditions"]["芝"] = turf
    if dirt is not None:
        result["surfaceConditions"]["ダート"] = dirt
    if surface == "障害":
        going = parse_jra_obstacle_going(result["surfaceConditions"])
    else:
        going = result["surfaceConditions"].get(surface)
    if going is not None:
        result["condition"] = going
    return result
