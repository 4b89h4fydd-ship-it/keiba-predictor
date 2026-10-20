"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _snapshot_final(detail: dict) -> bool:
    result=detail.get("result") or {}
    return result.get("status")=="確定" and bool(result.get("finishers"))
