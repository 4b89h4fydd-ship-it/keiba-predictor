"""Read-only FastAPI saved-data adapter; never collects or persists anything.

This is a branch-only opt-in into the existing race detail route. A caller
supplies the current canonical prepared/race-store resolver as a getter.
"""
from __future__ import annotations

from typing import Any, Callable

from arvexq.v3.transport.storage import read_saved
from arvexq.v3.transport.api import factual_response
from arvexq.v3.transport.display import factual_screen


def saved_fact_screen(race_id: str, getter: Callable[[str], Any]) -> dict | None:
    if not isinstance(race_id, str) or not race_id:
        raise ValueError("race ID required")
    if race_id.startswith("jra-"):
        circuit = "jra"
    elif race_id.startswith("nar-"):
        circuit = "nar"
    else:
        raise ValueError("unknown circuit in race ID")
    original = read_saved(getter, race_id, circuit=circuit)
    if original is None:
        return None
    # Always pre-race factual: even an archived race's postrace results,
    # sealed selections and past forecast models cannot enter this view.
    api_dto = factual_response(original, include_results=False)
    screen = factual_screen(api_dto)
    if screen.get("predictionStatus") != "not-implemented":
        raise ValueError("forecast status unexpectedly enabled")
    return screen
