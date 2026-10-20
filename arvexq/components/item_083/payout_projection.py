"""Owned observed trifecta payout view; shared parser still owns acquisition."""
from copy import deepcopy
from arvexq.v3.data.result_facts import PAYOUT_FIELDS, _observed, _result

_KINDS = ("3連単", "３連単", "三連単")


def read(detail, circuit):
    result = _result(detail, circuit)
    rows = result.get("payouts") if result else None
    if not isinstance(rows, list):
        return []
    output = []
    for row in rows:
        if not isinstance(row, dict) or row.get("kind") not in _KINDS:
            continue
        output.append({name: deepcopy(row[name]) for name in PAYOUT_FIELDS
                       if name in row and _observed(row[name])})
    return output
