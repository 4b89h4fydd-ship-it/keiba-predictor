"""Observed result field projections, never bets, payouts inferred from odds, or model.

Every field read is independent and circuit-checked. These are read-only
views of the ONE existing saved race result; not new acquisition routes.
"""
from __future__ import annotations

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
    """Only original, nonblank values for one finisher field.

    Missing rank/clock/margin is *not* guessed from array ordering.
    A source may use both 'finish' and 'rank'; preserve what it supplied.
    """
    if field not in FINISH_FIELDS:
        raise ValueError("unrecognized finish field")
    result = _result(detail, circuit)
    rows = result.get("finishers") if result else None
    if not isinstance(rows, list):
        return []
    fields = FINISH_FIELDS[field]
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        selected = {key: deepcopy(row[key]) for key in fields
                    if key in row and _observed(row[key])}
        if not selected:
            continue
        item = {"horseNumber": deepcopy(row.get("horseNumber"))}
        item.update(selected)
        output.append(item)
    return output


def payout_field(detail: dict[str, Any], circuit: str, kind: str) -> list[dict]:
    """Match an explicit existing payout *kind*, not its bet probability."""
    if kind not in PAYOUT_KINDS:
        raise ValueError("unrecognized payout kind")
    result = _result(detail, circuit)
    rows = result.get("payouts") if result else None
    if not isinstance(rows, list):
        return []
    names = PAYOUT_KINDS[kind]
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("kind") not in names:
            continue
        # Preserve observed kind/combination/payout without interpreting a
        # blank amount as a loss or making up a missing payout.
        output.append({key: deepcopy(row[key]) for key in PAYOUT_FIELDS
                       if key in row and _observed(row[key])})
    return output


def unmapped_payout_count(detail: dict[str, Any], circuit: str) -> int:
    """Separate unsupported kind labels from genuine no-payout evidence."""
    result = _result(detail, circuit)
    rows = result.get("payouts") if result else None
    if not isinstance(rows, list):
        return 0
    known = {name for names in PAYOUT_KINDS.values() for name in names}
    return sum(isinstance(row, dict) and row.get("kind") not in known
               for row in rows)
