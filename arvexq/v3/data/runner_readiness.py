"""Read-only per-runner saved history and odds evidence, never prediction."""
from __future__ import annotations
from typing import Any
from arvexq.v3.data.observed_fields import ensure_circuit, history
from arvexq.v3.data.odds_facts import missing_status

def read_runner_readiness(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    ensure_circuit(detail, circuit)
    histories = history(detail, circuit)
    quotes = missing_status(detail, circuit)
    if len(histories) != len(quotes):
        raise ValueError("runner history/market evidence misalignment")
    result = []
    for past, market in zip(histories, quotes):
        if past["horseNumber"] != market["horseNumber"]:
            raise ValueError("runner identity mismatch in evidence")
        count = past["observedPriorRunCount"]
        win, place, popularity = (market[k] for k in ("win", "place", "popularity"))
        result.append({
            "schema": "arvexq-v3-runner-readiness-1",
            "horseNumber": past["horseNumber"],
            "history": "partial-unverified" if count > 0 else "missing",
            "observedPriorRunCount": count,
            "allCareerRunsVerified": False,
            "odds": "observed-unverified" if win == place == "observed" else "incomplete",
            "win": win, "place": place, "popularity": popularity,
            "marketFreshnessVerified": False,
            "canClaimFullyRetrieved": False,
        })
    return result
