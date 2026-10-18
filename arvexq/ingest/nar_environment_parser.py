"""Compose independent NAR weather, going and scratch extractors.

Preserve the existing API payload, leaving unavailable observations absent.
"""
import re
from bs4 import BeautifulSoup
from arvexq.ingest.nar_weather import parse_nar_weather
from arvexq.ingest.nar_going import parse_nar_going, parse_nar_going_moisture
from arvexq.ingest.nar_scratches import parse_nar_scratches

def _parse_nar_environment_html(html: str) -> dict:
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    result = {"scratchMap": parse_nar_scratches(soup)}
    weather = parse_nar_weather(text)
    going = parse_nar_going(text)
    moisture = parse_nar_going_moisture(text)
    if weather is not None:
        result["weather"] = weather
    if going is not None:
        result["condition"] = going
    if moisture is not None:
        result["goingMoisture"] = moisture
    return result
