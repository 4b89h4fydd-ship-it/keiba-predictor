"""Strict field allowlists for independent v3 observation views.

Raw data stays with the existing collector; never turn missing facts into zeros,
never include former prediction marks, learned scores or betting receipts.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from arvexq.ingest.full_career import merge_career
from arvexq.v3.data.quality import normalize_circuit

RACE = ("id", "date", "circuit", "track", "raceNumber", "title", "surface",
        "distance", "condition", "weather", "startTime", "fieldSize", "racePrize1")
RUNNER = ("horseNumber", "frameNumber", "name", "sex", "age", "jockey",
          "trainer", "affiliation", "carriedWeight", "bodyWeight",
          "bodyWeightChange", "status", "scratched", "withdrawn")
HISTORY = ("date", "track", "surface", "distance", "condition", "weather",
           "finish", "rank", "timeSeconds", "time", "margin", "last3f",
           "cornerPositions", "passing", "jockey", "carriedWeight",
           "fieldSize", "className", "grade", "raceId")
ODDS = ("winOdds", "placeOdds", "popularity")
FINISHER = ("horseNumber", "frameNumber", "name", "finish", "rank",
            "timeSeconds", "time", "margin", "last3f", "cornerPositions")
PAYOUT = ("kind", "combination", "combo", "payout", "amount", "popularity")


def ensure_circuit(detail: dict[str, Any], expected: str) -> None:
    """Fail closed rather than reinterpret an unknown/cross-circuit race."""
    if not isinstance(detail, dict):
        raise ValueError("observed race detail mapping required")
    actual = normalize_circuit(detail.get("circuit"))
    if actual != expected:
        raise ValueError("wrong or unknown racing circuit")
    rid = str(detail.get("id") or "")
    if rid.startswith(("jra-", "nar-")) and not rid.startswith(expected + "-"):
        raise ValueError("race ID contradicts circuit")


def select(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {name: deepcopy(source[name]) for name in fields if name in source}


def race(detail: dict[str, Any], circuit: str) -> dict[str, Any]:
    ensure_circuit(detail, circuit)
    return select(detail, RACE)


def entries(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    ensure_circuit(detail, circuit)
    return [select(h, RUNNER) for h in detail.get("horses", [])
            if isinstance(h, dict)]


def history(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    ensure_circuit(detail, circuit)
    result: list[dict[str, Any]] = []
    # A horse's history always remains attached to its original runner row;
    # no matching on name or horse number here.
    for horse in detail.get("horses", []):
        if not isinstance(horse, dict):
            continue
        observed = merge_career(
            horse.get("allPastRuns"), horse.get("recentRaces"), detail.get("date")
        )
        result.append({
            "horseNumber": deepcopy(horse.get("horseNumber")),
            "pastRuns": [select(h, HISTORY) for h in observed],
            "observedPriorRunCount": len(observed),
            "careerCompleteness": "unverified",
        })
    return result


def odds(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    ensure_circuit(detail, circuit)
    # Quotes are snapshots only. No inferred payoff, time or betting advice.
    return [
        {"horseNumber": deepcopy(h.get("horseNumber")), **select(h, ODDS)}
        for h in detail.get("horses", []) if isinstance(h, dict)
    ]


def results(detail: dict[str, Any], circuit: str) -> dict[str, Any]:
    ensure_circuit(detail, circuit)
    raw = detail.get("result")
    if not isinstance(raw, dict):
        return {"resultState": "not-observed", "finishers": [], "payouts": []}
    finishers = raw.get("finishers")
    payouts = raw.get("payouts")
    return {
        # Even a supplied result cannot be certified as official/final without
        # independent confirmation from the existing canonical result pipeline.
        "resultState": "observed-unverified",
        "finishers": [select(r, FINISHER) for r in finishers
                      if isinstance(r, dict)] if isinstance(finishers, list) else [],
        "payouts": [select(r, PAYOUT) for r in payouts
                    if isinstance(r, dict)] if isinstance(payouts, list) else [],
    }
