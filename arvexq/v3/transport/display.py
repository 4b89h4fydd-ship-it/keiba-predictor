"""Read-only mobile-neutral view DTO; screen markup/CSS remain existing owners.

Separating formatting from saved storage prevents the browser from recalculating
forecast, marks or tickets and prevents retroactive original exposure.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def factual_screen(response: dict[str, Any], *, recent_limit: int = 5) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("schema") != "arvexq-v3-factual-api-1":
        raise ValueError("v3 factual API response required")
    if isinstance(recent_limit, bool) or not isinstance(recent_limit, int) or not 0 <= recent_limit <= 20:
        raise ValueError("recent_limit must be an integer between zero and twenty")
    entries = response.get("entries")
    history = response.get("history")
    odds = response.get("odds")
    if not isinstance(entries, list) or not isinstance(history, list) or not isinstance(odds, list):
        raise ValueError("incomplete observed response")
    if not len(entries) == len(history) == len(odds):
        raise ValueError("runner/history/odds alignment mismatch")
    # Preserve source row identity and refuse ambiguous duplicates, not a
    # fabricated index/name merge that could attach another horse's history.
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for h, past, price in zip(entries, history, odds):
        number = h.get("horseNumber")
        if isinstance(number, bool):
            raise ValueError("invalid runner number")
        try:
            actual = int(number)
        except (ValueError, TypeError, OverflowError):
            raise ValueError("invalid runner number") from None
        if actual <= 0 or actual in seen or number != past.get("horseNumber") or number != price.get("horseNumber"):
            raise ValueError("runner identity collision/misalignment")
        seen.add(actual)
        runs = past.get("pastRuns")
        if not isinstance(runs, list):
            raise ValueError("past run list missing")
        rows.append({
            "horseNumber": actual,
            "horse": deepcopy(h),
            "odds": deepcopy({k: v for k, v in price.items() if k != "horseNumber"}),
            "recentRaces": deepcopy(runs[:recent_limit]),
            "observedPriorRunCount": past["observedPriorRunCount"],
            "careerCompleteness": "unverified",
        })
    rows.sort(key=lambda row: row["horseNumber"])
    return {
        "schema": "arvexq-v3-factual-screen-1",
        "race": deepcopy(response.get("race")),
        "rows": rows,
        "results": deepcopy(response.get("results")) if response.get("resultsIncluded") else None,
        "coverage": deepcopy(response.get("coverage")),
        "predictionStatus": "not-implemented",
        "marks": None,
        "tickets": None,
    }
