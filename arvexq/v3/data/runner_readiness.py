"""Read-only per-runner saved history and odds evidence, never prediction."""
from __future__ import annotations
from typing import Any
from math import isfinite
from arvexq.v3.data.observed_fields import ensure_circuit, history
from arvexq.v3.data.odds_facts import missing_status

def read_runner_readiness(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    ensure_circuit(detail, circuit)
    histories = history(detail, circuit)
    quotes = missing_status(detail, circuit)
    if len(histories) != len(quotes):
        raise ValueError("runner history/market evidence misalignment")
    raw = detail.get("horses")
    if not isinstance(raw, list) or len(raw) != len(histories):
        raise ValueError("runner field evidence misalignment")
    result = []
    for horse, past, market in zip(raw, histories, quotes):
        if not isinstance(horse, dict) or horse.get("horseNumber") != past["horseNumber"]:
            raise ValueError("runner identity mismatch in basic fields")
        if past["horseNumber"] != market["horseNumber"]:
            raise ValueError("runner identity mismatch in evidence")
        count = past["observedPriorRunCount"]
        win, place, popularity = (market[k] for k in ("win", "place", "popularity"))
        basic_fields = {}
        for key in ("name", "jockey", "trainer", "carriedWeight"):
            value = horse.get(key)
            basic_fields[key] = ("missing" if value is None or
                                 isinstance(value, str) and value.strip() in
                                 ("", "-", "--", "不明") else
                                 "invalid" if isinstance(value, bool) or
                                 isinstance(value, float) and not isfinite(value)
                                 else "observed")
        reasons = {}
        for key in basic_fields:
            value = horse.get(key)
            reasons[key] = ("absent" if key not in horse else
                            "null" if value is None else
                            "placeholder" if isinstance(value, str) and
                            value.strip() in ("", "-", "--", "不明") else
                            "invalid-type-or-number" if basic_fields[key] == "invalid"
                            else "saved-value")
        result.append({
            "basicFields": basic_fields,
            "basicFieldReasons": reasons,
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
