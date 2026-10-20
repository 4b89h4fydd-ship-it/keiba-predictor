"""Compose JRA/NAR independently observed quote fields, without guessing odds."""
from __future__ import annotations
from importlib import import_module
from typing import Any

from arvexq.v3.data.observed_fields import ensure_circuit

FIELDS = ("win_odds", "place_odds", "popularity", "quote_time")


def read_quotes(detail: dict[str, Any], circuit: str) -> dict[str, Any]:
    ensure_circuit(detail, circuit)
    fields = {}
    for name in FIELDS:
        rows = import_module(f"arvexq.v3.data.{circuit}.quote_fields.{name}").read(detail)
        fields[name] = {
            "rows": rows,
            "observed": sum(r["status"].startswith("observed") for r in rows),
            "missing": sum(r["status"] == "missing" for r in rows),
            "invalid": sum(r["status"] == "invalid" for r in rows),
        }
    return {
        "schema": "arvexq-v3-observed-quote-fields-1",
        "circuit": circuit,
        "fields": fields,
        "quoteFreshness": "unknown",
        "quoteTimeIndependentVerified": False,
        "notModelProbabilities": True,
    }
