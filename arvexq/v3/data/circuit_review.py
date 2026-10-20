"""Independent JRA/NAR fact readers joined only for coverage accounting.

The shared orchestration does not fetch or overwrite any record, never passes
post-race information to a future pre-race predictor, and never emits marks/bets.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from arvexq.v3.data.quality import build_data_status, normalize_circuit

DOMAINS = ("race", "entries", "history", "odds", "results")


def inspect_circuit(detail: dict[str, Any] | None) -> dict[str, Any]:
    status = build_data_status(detail)
    circuit = normalize_circuit((detail or {}).get("circuit")) if isinstance(detail, dict) else None
    base = {
        "schema": "arvexq-v3-circuit-coverage-1",
        "circuit": circuit,
        "source": "existing-snapshot",
        "domains": {domain: "unavailable" for domain in DOMAINS},
        "dataStatus": status["status"],
        "warnings": list(status["warnings"]),
        "historyCompleteness": "unverified",
        "predictionStatus": "not-implemented",
    }
    if circuit is None or not isinstance(detail, dict):
        return base
    try:
        observed = {
            domain: import_module(f"arvexq.v3.data.{circuit}.{domain}").read(detail)
            for domain in DOMAINS
        }
    except ValueError as exc:
        base["warnings"].append("circuit-routing-refused")
        base["routingError"] = str(exc)
        return base
    entries = observed["entries"]
    history = observed["history"]
    odds = observed["odds"]
    results = observed["results"]
    base["domains"] = {
        "race": "observed" if observed["race"].get("id") else "missing",
        "entries": "observed" if entries else "missing",
        "history": "observed" if any(x["pastRuns"] for x in history) else "missing",
        "odds": "observed" if any(any(k in x and x[k] is not None for k in
                                     ("winOdds", "placeOdds", "popularity")) for x in odds) else "missing",
        "results": results["resultState"],
    }
    base["counts"] = {
        "runnerRows": len(entries),
        "observedPriorRuns": sum(x["observedPriorRunCount"] for x in history),
        "runnersWithPriorRuns": sum(bool(x["pastRuns"]) for x in history),
        "oddsHorseRows": sum(any(k in x and x[k] is not None for k in
                                 ("winOdds", "placeOdds", "popularity")) for x in odds),
        "resultFinishers": len(results["finishers"]),
        "resultPayoutRows": len(results["payouts"]),
    }
    return base
