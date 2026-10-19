"""Owned post-race corners projection, not inferred from missing or future results."""
from copy import deepcopy
from arvexq.v3.data.result_facts import _observed, _result

_FIELDS = ("cornerPositions","passing")


def read(detail, circuit):
    result = _result(detail, circuit)
    rows = result.get("finishers") if result else None
    if not isinstance(rows, list):
        return []
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        selected = {name: deepcopy(row[name]) for name in _FIELDS
                    if name in row and _observed(row[name])}
        if not selected:
            continue
        entry = {"horseNumber": deepcopy(row.get("horseNumber"))}
        entry.update(selected)
        output.append(entry)
    return output
