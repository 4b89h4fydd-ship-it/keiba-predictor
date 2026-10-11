"""Small, source-neutral contract for using D1-persisted racing evidence.

This module fetches nothing. The existing canonical prefetch collects facts;
the existing D1 sync stores them. AI is allowed to consume only D1 readbacks.
"""
from __future__ import annotations

from typing import Any


def _runners(detail: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for h in detail.get("horses") or []:
        if not isinstance(h, dict):
            continue
        try:
            number = int(h.get("horseNumber") or 0)
        except (ValueError, TypeError):
            continue
        if number > 0 and str(h.get("name") or "").strip():
            out[number] = h
    return out


def verify_persisted_facts(source: dict[str, Any], saved: dict[str, Any]) -> list[str]:
    """Return precise missing/mismatched records; never replace failed writes with RAM.

    Compare the same race IDs, horse identities, and complete-history cardinality.
    Both D1 summary and detail must exist. An incomplete official source is not
    treated as proof that a horse had no earlier runs.
    """
    expected = [r for r in (source.get("summaries") or source.get("races") or [])
                if isinstance(r, dict) and r.get("id")]
    source_details = {str(x["id"]): x for x in (source.get("details") or [])
                      if isinstance(x, dict) and x.get("id")}
    saved_ids = {str(x["id"]) for x in (saved.get("races") or [])
                 if isinstance(x, dict) and x.get("id")}
    saved_details = {str(x["id"]): x for x in (saved.get("details") or [])
                     if isinstance(x, dict) and x.get("id")}
    errors: list[str] = []
    for row in expected:
        rid = str(row["id"])
        old = source_details.get(rid)
        new = saved_details.get(rid)
        if rid not in saved_ids:
            errors.append(f"{rid}:summary-not-saved")
        if not isinstance(old, dict) or not old.get("id"):
            errors.append(f"{rid}:collected-detail-missing")
            continue
        if not isinstance(new, dict):
            errors.append(f"{rid}:detail-not-saved")
            continue
        if str(new.get("date") or "") != str(old.get("date") or ""):
            errors.append(f"{rid}:date-mismatch")
        a, b = _runners(old), _runners(new)
        if set(a) != set(b) or any(str(a[n].get("name")) != str(b[n].get("name")) for n in a.keys() & b.keys()):
            errors.append(f"{rid}:horse-identities-changed")
        for number in a.keys() & b.keys():
            # A saved snapshot may have additional history, but must not lose
            # any already collected official career evidence.
            for key in ("allPastRuns", "recentRaces"):
                collected = a[number].get(key)
                stored = b[number].get(key)
                if isinstance(collected, list) and len(collected) > len(stored or []):
                    errors.append(f"{rid}:horse-{number}:{key}-truncated")
    return errors

def may_create_prerace_prediction(detail: dict[str, Any], now=None) -> bool:
    """No newly generated pre-race marks once the official scheduled off time passes."""
    from datetime import datetime, timedelta, timezone

    if not isinstance(detail, dict):
        return False
    day = str(detail.get("date") or "")
    clock = str(detail.get("scheduledStartTime") or detail.get("startTime") or "")
    try:
        off = datetime.strptime(day + " " + clock[:5], "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone(timedelta(hours=9))
        )
    except (TypeError, ValueError):
        return False
    if now is None:
        now = datetime.now(off.tzinfo)
    return now < off
