"""Observed result field projections, never bets, payouts inferred from odds, or model.

Every field read is independent and circuit-checked. These are read-only
views of the ONE existing saved race result; not new acquisition routes.
"""
from __future__ import annotations

from importlib import import_module
from copy import deepcopy
from typing import Any

from arvexq.v3.data.observed_fields import ensure_circuit

FINISH_FIELDS = {
    "finish": ("finish", "rank"),
    "margin": ("margin",),
    "clock": ("time", "timeSeconds"),
    "corners": ("cornerPositions", "passing"),
}
PAYOUT_KINDS = {
    "win": ("単勝",),
    "place": ("複勝",),
    "frame_quinella": ("枠連",),
    "quinella": ("馬連",),
    "wide": ("ワイド",),
    "exacta": ("馬単",),
    "trio": ("3連複", "３連複", "三連複"),
    "trifecta": ("3連単", "３連単", "三連単"),
}
PAYOUT_FIELDS = ("kind", "combination", "combo", "payout", "amount", "popularity")
_FINISH_OWNER = {"finish":70,"margin":71,"clock":72,"corners":75}
_PAYOUT_OWNER = {"win":76,"place":77,"frame_quinella":78,"quinella":79,"wide":80,"exacta":81,"trio":82,"trifecta":83}



def _observed(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip() not in ("-", "--", "不明")
    return value not in ([], {})


def _result(detail: dict[str, Any], circuit: str) -> dict | None:
    ensure_circuit(detail, circuit)
    raw = detail.get("result")
    return raw if isinstance(raw, dict) else None


def finish_field(detail: dict[str, Any], circuit: str, field: str) -> list[dict]:
    """Dispatch an observed finisher projection to its responsibility owner."""
    if field not in FINISH_FIELDS:
        raise ValueError("unrecognized finish field")
    return import_module("arvexq.components.item_" + f"{_FINISH_OWNER[field]:03d}" + ".result_projection").read(detail, circuit)

def payout_field(detail: dict[str, Any], circuit: str, kind: str) -> list[dict]:
    """Dispatch an observed payout projection to its responsibility owner."""
    if kind not in PAYOUT_KINDS:
        raise ValueError("unrecognized payout kind")
    return import_module("arvexq.components.item_" + f"{_PAYOUT_OWNER[kind]:03d}" + ".payout_projection").read(detail, circuit)

def unmapped_payout_count(detail: dict[str, Any], circuit: str) -> int:
    """Separate unsupported kind labels from genuine no-payout evidence."""
    result = _result(detail, circuit)
    rows = result.get("payouts") if result else None
    if not isinstance(rows, list):
        return 0
    known = {name for names in PAYOUT_KINDS.values() for name in names}
    return sum(isinstance(row, dict) and row.get("kind") not in known
               for row in rows)
