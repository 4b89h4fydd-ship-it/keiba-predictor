"""Join only saved-odds field contracts, never derive new market prices."""
from __future__ import annotations

from importlib import import_module
from typing import Any

from arvexq.v3.data.observed_fields import ensure_circuit
from arvexq.v3.data.odds_facts import FIELDS


def read_odds_breakdown(detail: dict[str, Any], circuit: str) -> dict[str, Any]:
    ensure_circuit(detail, circuit)
    data = {
        key: import_module(f"arvexq.v3.data.{circuit}.odds_fields.{key}").read(detail)
        for key in FIELDS
    }
    counts = {key: {
        status: sum(x["state"] == status for x in data[key])
        for status in ("observed", "missing", "invalid")
    } for key in ("win", "place", "popularity", "delta")}
    return {
        "schema": "arvexq-v3-observed-odds-fields-1",
        "circuit": circuit,
        "runnerRows": len(data["win"]),
        "win": data["win"],
        "place": data["place"],
        "popularity": data["popularity"],
        "delta": data["delta"],
        "timestamp": data["timestamp"],
        "source": data["source"],
        "missing": data["missing"],
        "counts": counts,
        "marketDateAndPreOffVerified": False,
        "liveMarketFreshnessVerified": False,
        "predictionsCalculated": False,
    }
