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
    race = response.get("race") or {}
    expected = race.get("fieldSize") if isinstance(race, dict) else None
    roster = ("count-mismatch" if type(expected) is int and expected > 0
              and expected != len(rows) else "unverified")
    observed_runs = sum(len(row["recentRaces"]) for row in rows)
    history_state = "missing" if observed_runs == 0 else "partial-unverified"
    prices = response.get("oddsFields") or {}
    win = prices.get("win", []) if isinstance(prices, dict) else []
    place = prices.get("place", []) if isinstance(prices, dict) else []
    def valid_count(values):
        return sum(item.get("state") == "observed" for item in values
                   if isinstance(item, dict)) if isinstance(values, list) else 0
    odds_state = ("observed-unverified" if len(rows) and
                  valid_count(win) == len(rows) and valid_count(place) == len(rows)
                  else "incomplete")
    readiness = {
        "schema": "arvexq-v3-display-readiness-1",
        "complete": False,
        "roster": roster,
        "history": history_state,
        "odds": odds_state,
        "message": "保存済み観測データのみ。全項目の取得完了は未確認",
        "canClaimFullyRetrieved": False,
        "predictionsEnabled": False,
    }
    return {
        "schema": "arvexq-v3-factual-screen-1",
        "race": deepcopy(response.get("race")),
        "rows": rows,
        "results": deepcopy(response.get("results")) if response.get("resultsIncluded") else None,
        "resultFields": deepcopy(response.get("resultFields")) if response.get("resultsIncluded") else None,
        "coverage": deepcopy(response.get("coverage")),
        "oddsFields": deepcopy(response.get("oddsFields")),
        "quoteFields": deepcopy(response.get("quoteFields")),
        "displayReadiness": readiness,
        "predictionStatus": "not-implemented",
        "marks": None,
        "tickets": None,
    }
