#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select only D1 race details that actually need full-prefetch repair.

Full Prefetch may build >100 MB for a full day. Rewriting every rich race on
each run overloads the Worker/D1 write path. Existing rich race details are
left in place; missing/thin details are republished from the freshly prepared
payload. Summaries remain cheap and are always refreshed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def meaningful(v: Any) -> bool:
    return v not in (None, "", [], {})


def named_roster(detail: Any) -> dict[int, str]:
    """Valid named runners keyed by the canonical horse number."""
    result: dict[int, str] = {}
    if not isinstance(detail, dict):
        return result
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        try:
            number = int(horse.get("horseNumber") or 0)
        except (TypeError, ValueError):
            continue
        name = str(horse.get("name") or "").strip()
        if number > 0 and name:
            result[number] = name
    return result


def rich(detail: Any) -> bool:
    if not isinstance(detail, dict) or not detail.get("id"):
        return False
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    roster = named_roster(detail)
    if len(roster) < 2 or len(roster) != len(horses):
        return False
    pm = detail.get("preparedMeta") if isinstance(detail.get("preparedMeta"), dict) else {}
    return bool(pm.get("diagnosisReady")) or any(
        meaningful(detail.get(k))
        for k in ("preRacePrediction", "aiEvaluation", "pace", "pacePrediction", "volatility")
    )


def repair_reason(prepared: Any, existing: Any) -> str:
    """A rich-but-truncated D1 card also needs repair; never drop known runners."""
    if not isinstance(prepared, dict) or not prepared.get("id"):
        return ""
    if existing is None:
        return "missing"
    if not isinstance(existing, dict) or str(existing.get("id") or "") != str(prepared["id"]):
        return "race_id_mismatch"
    new = named_roster(prepared)
    old = named_roster(existing)
    if len(new) >= len(old) and (not old.keys() <= new.keys() or len(new) > len(old)):
        return "roster_incomplete"
    if not rich(existing):
        return "thin"
    return ""

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prepared", required=True)
    p.add_argument("--current", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()

    prepared = read(args.prepared)
    current = read(args.current)
    current_by_id = {
        str(d.get("id")): d
        for d in (current.get("details") or [])
        if isinstance(d, dict) and d.get("id")
    }
    wanted = [d for d in (prepared.get("details") or []) if isinstance(d, dict) and d.get("id")]

    selected: list[dict[str, Any]] = []
    reasons: list[dict[str, str]] = []
    for detail in wanted:
        rid = str(detail.get("id") or "")
        old = current_by_id.get(rid)
        reason = repair_reason(detail, old)
        if reason:
            # A damaged source must not erase a larger D1 roster.
            if old and len(named_roster(detail)) < len(named_roster(old)):
                reasons.append({"race_id": rid, "reason": "source_roster_smaller_not_replaced"})
                continue
            selected.append(detail)
            reasons.append({"race_id": rid, "reason": reason})

    meta = dict(prepared.get("meta") or {})
    meta.update({
        "source": "github-actions-full-prefetch-repair-only-v1",
        "prepared_detail_count": len(wanted),
        "existing_detail_count": len(current_by_id),
        "repair_detail_count": len(selected),
    })
    out = {
        "summaries": prepared.get("summaries") or [],
        "details": selected,
        "meta": meta,
    }
    report = {
        "prepared": len(wanted),
        "existing": len(current_by_id),
        "existing_rich": sum(1 for d in current_by_id.values() if rich(d)),
        "repair_count": len(selected),
        "repairs": reasons,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "PREFETCH_REPAIR_SELECTION",
        f"prepared={report['prepared']}",
        f"existing={report['existing']}",
        f"existing_rich={report['existing_rich']}",
        f"repair_count={report['repair_count']}",
    )
    for item in reasons[:30]:
        print("PREFETCH_REPAIR", item["race_id"], item["reason"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
