"""Complete missing NAR margin seconds from the system's own stored results.

The observed margin factor (arvexq.prediction.observed_evidence) needs the
measured seconds behind the winner for each past run. Runs imported through
the official NAR CSV carry ``marginSeconds`` plus a ``marginEvidence``
proof, but runs collected through the newer forward route carry only
``marginText`` (lengths, as text) and the horse's own ``timeSeconds`` — no
winner time — so the margin factor stayed unavailable for those horses
(2026-11-19: ~37 of 395 horses, e.g. 6 of 13 in Ooi 1R).

This module heals such a run from the result record the system itself has
already stored for that past race (the detail store read back through the
injected fetchers). The winner's ``timeSeconds`` is taken from the stored
race's finishers and ``marginSeconds = own time - winner time`` is written
as a measured record, never an estimate:

- The stored race must be identified unambiguously: by the run's raceId,
  by date/track/raceNumber, or by scanning that date's stored races.
- The stored race must contain exactly one finisher row for this horse
  whose finish and time agree with the run's own recorded facts. Any
  disagreement or ambiguity leaves the run untouched.
- A negative gap, a missing own time, or a missing winner time leaves the
  run untouched. The winner's own run completes as exactly 0.0.
- The provenance is labelled honestly as ``arvexq_result_store`` — the
  value comes from the system's stored result record, not from the
  official CSV (``nar_official_csv``) and not from a JRA official proof.

Only the five most recent starts per horse are considered: those are the
runs the margin score reads (observed_runs with limit=5), so older career
rows are never fetched for. JRA races are never completed here: the JRA
margin gate (``_verified_jra_proof`` in observed_evidence) keeps
requiring an official result proof, unchanged.

Completion runs at analyze input assembly (scripts/arvexq_prefetch
``_decorate``), before attach_evidence, so it consults the result store as
it stands at analysis time: a result stored after the card was collected
is still picked up on the next analysis pass. This module fetches nothing
itself; the caller injects the store accessors.
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable

SOURCE_LABEL = "arvexq_result_store"
RUN_KEYS = ("recentRaces", "allPastRuns", "pastRaces", "history", "runs")
JRA_CIRCUITS = ("中央", "JRA", "central")
# The margin score reads at most the five most recent observed runs.
SCORE_WINDOW = 5
# Same plausibility window the official-CSV / legacy backfills apply.
MAX_GAP_SECONDS = 30.0
# Stored times are rounded to 0.1s; the run's own time must agree.
TIME_TOLERANCE = 0.051

FetchRace = Callable[[str], "dict[str, Any] | None"]
FetchDayIds = Callable[[str], "list[str]"]


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    out = _num(value)
    return int(out) if out is not None else None


def _date_key(value: Any) -> str:
    text = str(value or "").strip().replace("/", "-").replace(".", "-")
    if re.fullmatch(r"\d{8}", text):
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]) else ""


def _has_margin(run: dict[str, Any]) -> bool:
    return any(run.get(key) not in (None, "") for key in ("marginSeconds", "timeBehindWinner"))


def _score_eligible(run: dict[str, Any]) -> bool:
    """Whether the margin score could read this run at all."""
    finish = _int(run.get("finish"))
    if finish is None or finish < 1:
        return False
    field = _int(run.get("fieldSize"))
    if field is not None and (field < 2 or finish > field):
        return False
    return _num(run.get("timeSeconds")) is not None


def _finishers(stored: dict[str, Any]) -> list[dict[str, Any]]:
    """Finisher rows of a stored race detail, from its result record."""
    result = stored.get("result")
    rows = result.get("finishers") if isinstance(result, dict) else None
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    # Some stored shapes carry the outcome on the horse rows instead.
    out = []
    for horse in stored.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        finish = _int(horse.get("finish"))
        if finish is not None and finish >= 1:
            out.append(horse)
    return out


def _winner_time(finishers: list[dict[str, Any]]) -> float | None:
    times = [_num(f.get("timeSeconds")) for f in finishers
             if _int(f.get("finish")) == 1]
    valid = [t for t in times if t is not None and t > 0]
    return min(valid) if valid else None


def _verify_finisher(finishers: list[dict[str, Any]], name: str,
                     run: dict[str, Any]) -> dict[str, Any] | None:
    """The one stored finisher row that provably is this run's start.

    Identity is the horse's name (unique in a race); the row's finish and
    time must agree with the facts already recorded on the run. A name
    match with disagreeing facts means the records conflict, so the run
    is left untouched rather than completed from a doubtful row.
    """
    finish = _int(run.get("finish"))
    own = _num(run.get("timeSeconds"))
    if finish is None or finish < 1 or own is None:
        return None
    named = [f for f in finishers
             if name and str(f.get("name") or "").strip() == name]
    candidates = named
    if not candidates:
        number = _int(run.get("horseNumber"))
        if number is not None:
            candidates = [f for f in finishers
                          if _int(f.get("horseNumber")) == number]
    if len(candidates) != 1:
        return None
    row = candidates[0]
    if _int(row.get("finish")) != finish:
        return None
    stored_time = _num(row.get("timeSeconds"))
    if stored_time is None or abs(stored_time - own) > TIME_TOLERANCE:
        return None
    return row


def _resolve_margin(run: dict[str, Any], name: str, target_date: str,
                    fetch_race: FetchRace, fetch_day_ids: FetchDayIds | None,
                    cache: dict[str, dict[str, Any] | None],
                    day_cache: dict[str, list[str]]) -> dict[str, Any] | None:
    """Measured margin facts for one run from the stored result record.

    Returns the fields to write onto the run, or None when the stored
    record cannot prove them. Nothing is estimated: the gap is the
    difference of two stored times.
    """
    date = _date_key(run.get("date") or run.get("raceDate"))
    track = str(run.get("track") or "").strip()
    if not date or not track or date >= target_date:
        return None
    race_ids: list[str] = []
    rid = str(run.get("raceId") or "").strip()
    if rid:
        race_ids.append(rid)
    else:
        number = _int(run.get("raceNumber") or run.get("raceNo"))
        if number is not None and 1 <= number <= 99:
            race_ids.append(f"nar-{date}-{track}-{number:02d}")
        elif fetch_day_ids is not None:
            if date not in day_cache:
                try:
                    day_cache[date] = list(fetch_day_ids(date) or [])
                except Exception:
                    day_cache[date] = []
            race_ids.extend(day_cache[date])
    for candidate_id in race_ids:
        if candidate_id not in cache:
            try:
                cache[candidate_id] = fetch_race(candidate_id)
            except Exception:
                cache[candidate_id] = None
        stored = cache[candidate_id]
        if not isinstance(stored, dict):
            continue
        if _date_key(stored.get("date")) != date:
            continue
        if str(stored.get("track") or "").strip() != track:
            continue
        finishers = _finishers(stored)
        if not finishers:
            continue
        if _verify_finisher(finishers, name, run) is None:
            continue
        # Identity proven: this stored race is the run's start. From here
        # the answer comes from this race only — never from another one.
        winner = _winner_time(finishers)
        if winner is None:
            return None
        own = _num(run.get("timeSeconds"))
        gap = round(own - winner, 3)
        if gap < 0 or gap > MAX_GAP_SECONDS:
            return None
        if _int(run.get("finish")) == 1:
            gap = 0.0
        fields: dict[str, Any] = {
            "marginSeconds": gap,
            "timeBehindWinner": gap,
            "marginEvidence": {
                "winnerTimeSeconds": winner,
                "horseTimeSeconds": own,
            },
            "marginEvidenceSource": SOURCE_LABEL,
        }
        if not rid:
            fields["raceId"] = candidate_id
            number = _int(stored.get("raceNumber"))
            if number is not None and run.get("raceNumber") in (None, ""):
                fields["raceNumber"] = number
        return fields
    return None


def complete_detail_margins(detail: dict[str, Any], fetch_race: FetchRace,
                            fetch_day_ids: FetchDayIds | None = None) -> dict[str, int]:
    """Fill missing past-run margins in a race detail from stored results.

    Mutates the detail's run rows in place (the analyze stage persists the
    decorated detail, so the healed record is what gets stored, carrying
    its honest ``arvexq_result_store`` provenance). Returns counts:
    ``completed`` starts healed, ``unresolved`` starts in the scoring
    window that still lack a margin, ``horses_touched`` horses with at
    least one healed start. JRA details are returned untouched.
    """
    stats = {"completed": 0, "unresolved": 0, "horses_touched": 0}
    if not isinstance(detail, dict):
        return stats
    if str(detail.get("circuit") or "") in JRA_CIRCUITS:
        return stats
    target_date = _date_key(detail.get("date") or detail.get("raceDate"))
    if not target_date:
        return stats
    cache: dict[str, dict[str, Any] | None] = {}
    day_cache: dict[str, list[str]] = {}
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        name = str(horse.get("name") or "").strip()
        # Group every representation of each start by date: the same start
        # can appear in several run lists as separate dicts, and healing
        # any one of them is not enough — all copies are written.
        by_date: dict[str, list[dict[str, Any]]] = {}
        seen: set[int] = set()
        for key in RUN_KEYS:
            runs = horse.get(key)
            if not isinstance(runs, list):
                continue
            for run in runs:
                if not isinstance(run, dict) or id(run) in seen:
                    continue
                seen.add(id(run))
                date = _date_key(run.get("date") or run.get("raceDate"))
                if date and date < target_date:
                    by_date.setdefault(date, []).append(run)
        window = [date for date in sorted(by_date, reverse=True)
                  if any(_score_eligible(r) for r in by_date[date])][:SCORE_WINDOW]
        touched = False
        for date in window:
            copies = [r for r in by_date[date]
                      if not _has_margin(r) and _score_eligible(r)]
            if not copies:
                continue
            fields = _resolve_margin(copies[0], name, target_date,
                                     fetch_race, fetch_day_ids, cache, day_cache)
            if fields is None:
                stats["unresolved"] += 1
                continue
            for run in copies:
                run.update(fields)
            stats["completed"] += 1
            touched = True
        if touched:
            stats["horses_touched"] += 1
    return stats
