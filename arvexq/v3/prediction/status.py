"""Explicit statuses for unimplemented prediction components, no execution."""
from __future__ import annotations

from arvexq.v3.data.quality import normalize_circuit

UNITS = ("ability", "running_style", "pace", "probability", "marks", "tickets")


def components_status(circuit: str) -> dict:
    name = normalize_circuit(circuit)
    if name is None:
        raise ValueError("unknown racing circuit")
    return {
        "schema": "arvexq-v3-forecast-empty-1",
        "circuit": name,
        "status": "not-implemented",
        "components": {unit: "not-implemented" for unit in UNITS},
        "forecast": None,
        "marks": None,
        "tickets": None,
    }
