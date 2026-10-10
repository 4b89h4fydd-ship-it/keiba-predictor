#!/usr/bin/env python3
"""Merge only the morning-pick fields written by arvexq_morning_picks.js.

JavaScript re-serialisation turns integral floats (1.0) into integers (1).
Frozen pre-race evidence such as ``massFeatureSnapshot`` is hashed over its
exact Python JSON form, so passing the whole payload through Node silently
breaks every origin hash and the D1 push later refuses the race.  The Node
step is only allowed to add morning-pick fields; every other byte is taken
from the original Python payload.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MORNING_KEYS = frozenset({
    "morningPickVersion", "morningPickFixedAt", "morningPickScope",
    "morningSelected", "morningSelectedScore", "morningSpecial",
    "morningAssessed", "morningPrimaryType", "morningSelectedTypes",
    "morningSelectionReason", "morningTicketKinds", "morningTicketEvidence",
    "morningMarkSnapshot",
})
# Nested containers in which Node only sets the ``morningPicks`` entry.
NESTED_MORNING = ("volatility", "environmentMeta")


def _by_id(rows: Any) -> dict[str, dict[str, Any]]:
    return {str(r.get("id")): r for r in (rows or []) if isinstance(r, dict) and r.get("id")}


def merge_row(original: dict[str, Any], node: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(original)
    if not isinstance(node, dict):
        return out
    for key in MORNING_KEYS:
        if key in node:
            out[key] = node[key]
    for key in NESTED_MORNING:
        picks = (node.get(key) or {}).get("morningPicks") if isinstance(node.get(key), dict) else None
        if picks is not None:
            nested = dict(original.get(key) or {}) if isinstance(original.get(key), dict) else {}
            nested["morningPicks"] = picks
            out[key] = nested
    return out


def merge(original: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    out = dict(original)
    for section in ("summaries", "details"):
        if section not in original:
            continue
        node_rows = _by_id(node.get(section))
        out[section] = [merge_row(r, node_rows.get(str(r.get("id")))) if isinstance(r, dict) else r
                        for r in (original.get(section) or [])]
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True)
    p.add_argument("--node-output", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    original = json.loads(Path(args.original).read_text(encoding="utf-8"))
    node = json.loads(Path(args.node_output).read_text(encoding="utf-8"))
    merged = merge(original, node)
    Path(args.out).write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    print("MORNING_OUTPUT_MERGED_PRESERVING_PYTHON_BYTES",
          "details=" + str(len(merged.get("details") or [])),
          "summaries=" + str(len(merged.get("summaries") or [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
