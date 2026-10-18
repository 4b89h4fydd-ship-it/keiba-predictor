"""Factual HTTP response DTO generator; not an alternate public HTTP route.

Only use from an existing validated saved detail. A pre-race read NEVER exposes
results, payout, frozen original mark, or ticket information.
"""
from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from typing import Any

from arvexq.v3.data.observed_fields import ensure_circuit
from arvexq.v3.data.quality import normalize_circuit, build_data_status
from arvexq.v3.data.circuit_review import inspect_circuit, DOMAINS
from arvexq.v3.data.result_split import read_breakdown
from arvexq.v3.data.quote_split import read_quotes


def factual_response(detail: dict[str, Any], *, include_results: bool = False) -> dict[str, Any]:
    if not isinstance(detail, dict) or not isinstance(include_results, bool):
        raise ValueError("factual detail and result access flag required")
    circuit = normalize_circuit(detail.get("circuit"))
    if circuit is None:
        raise ValueError("unknown racing circuit")
    ensure_circuit(detail, circuit)

    # Independently tested circuit-owned projections use strict allowlists.
    read = lambda domain: import_module(f"arvexq.v3.data.{circuit}.{domain}").read(detail)
    race = read("race")
    if not race.get("id") or not race.get("date"):
        raise ValueError("cannot publish unidentifiable observed race")
    coverage = inspect_circuit(detail)
    if "circuit-routing-refused" in coverage["warnings"]:
        raise ValueError("race/circuit identity conflict")
    if not include_results:
        coverage = deepcopy(coverage)
        coverage["domains"]["results"] = "withheld-until-postrace"
        if "counts" in coverage:
            coverage["counts"]["resultFinishers"] = None
            coverage["counts"]["resultPayoutRows"] = None
    return {
        "schema": "arvexq-v3-factual-api-1",
        "circuit": circuit,
        "race": race,
        "entries": read("entries"),
        "history": read("history"),
        "odds": read("odds"),
        "oddsFields": read_quotes(detail, circuit),
        "results": read("results") if include_results else None,
        "resultFields": read_breakdown(detail, circuit) if include_results else None,
        "resultsIncluded": include_results,
        "coverage": coverage,
        "prediction": None,
        "marks": None,
        "tickets": None,
        "predictionStatus": "not-implemented",
    }
