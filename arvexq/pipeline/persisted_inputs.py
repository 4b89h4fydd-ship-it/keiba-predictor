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



def _career_rows(horse: dict[str, Any], cutoff: str) -> list[dict[str, Any]]:
    """Recover the existing packed career archive without any provider request."""
    if horse.get("careerArchive"):
        from arvexq.ingest.career_transport import recover_horse
        horse = recover_horse(horse, cutoff)
    # Full career and the display's latest five deliberately overlap.
    # Deduplicate the observations before comparing stored evidence counts.
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for race in [*(horse.get("allPastRuns") or []), *(horse.get("recentRaces") or [])]:
        if not isinstance(race, dict):
            continue
        identity = (
            str(race.get("date") or ""),
            str(race.get("raceId") or race.get("track") or ""),
            str(race.get("raceNumber") or ""),
            str(race.get("finish") or ""),
        )
        if identity == ("", "", "", ""):
            identity = (str(race), "", "", "")
        if identity not in seen:
            seen.add(identity)
            out.append(race)
    return out


def _history_observations_retained(original: list[dict[str, Any]],
                                   saved: list[dict[str, Any]]) -> bool:
    """Older results can gain fields; their known date/venue/race must survive."""
    keys = ("date", "track", "raceNumber", "raceId", "finish")
    for prior in original:
        known = [(k, str(prior[k])) for k in keys if prior.get(k) not in (None, "")]
        if known and not any(all(str(next_run.get(k, "")) == value for k, value in known)
                             for next_run in saved):
            return False
    return True


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
            # Recover the same canonical full-career transport used by the
            # existing prefetch. Five visible runs are not a complete career.
            try:
                original = _career_rows(a[number], str(old.get("date") or ""))
                retained = _career_rows(b[number], str(new.get("date") or ""))
            except (ValueError, KeyError, TypeError, RuntimeError) as exc:
                errors.append(f"{rid}:horse-{number}:career-archive-invalid:{type(exc).__name__}")
                continue
            # Original older starts must remain, even after compression.
            if not _history_observations_retained(original, retained):
                errors.append(f"{rid}:horse-{number}:allPastRuns-truncated")
            elif len(original) > len(retained):
                # Handle historical rows lacking any usable race identity.
                errors.append(f"{rid}:horse-{number}:history-count-truncated")
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
