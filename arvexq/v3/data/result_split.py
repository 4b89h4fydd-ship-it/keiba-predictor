"""Compose 12 independent circuit-owned fact readers, only post-race.

Nothing here decides official result finality, bets, predictions or payouts
that are absent from the original result. Do not expose to a pre-race consumer.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from arvexq.v3.data.observed_fields import ensure_circuit
from arvexq.v3.data.result_facts import FINISH_FIELDS, PAYOUT_KINDS, unmapped_payout_count

MODULES = ("finish", "margin", "clock", "corners",
           "win", "place", "frame_quinella", "quinella", "wide",
           "exacta", "trio", "trifecta")


def read_breakdown(detail: dict[str, Any], circuit: str) -> dict[str, Any]:
    ensure_circuit(detail, circuit)
    raw = detail.get("result")
    present = isinstance(raw, dict)
    independent = {}
    for name in MODULES:
        reader = import_module(f"arvexq.v3.data.{circuit}.result_fields.{name}").read
        values = reader(detail)
        independent[name] = {
            "status": ("not-observed" if not present else
                       "observed" if values else "field-not-observed"),
            "rows": values,
        }
    return {
        "schema": "arvexq-v3-observed-result-fields-1",
        "circuit": circuit,
        "resultState": "observed-unverified" if present else "not-observed",
        "finisherFields": {key: independent[key] for key in FINISH_FIELDS},
        "payoutKinds": {key: independent[key] for key in PAYOUT_KINDS},
        "unmappedPayoutRows": unmapped_payout_count(detail, circuit),
        "officialFinalityVerified": False,
        "predictionsCalculated": False,
    }
