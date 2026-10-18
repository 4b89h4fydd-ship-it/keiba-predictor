"""Read-only assessment of observed race facts, never a prediction grade.

The canonical JRA/NAR collector continues to own external access. This module
cannot fetch or persist anything, and never treats missing history as a first start.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from math import isfinite
from typing import Any

from arvexq.ingest.full_career import date_key, merge_career

RACE_FIELDS = ("id", "date", "track", "startTime", "surface", "distance")
HORSE_FIELDS = ("horseNumber", "name", "jockey", "trainer", "carriedWeight")
CIRCUITS = {
    "jra": "jra", "中央": "jra", "central": "jra",
    "nar": "nar", "地方": "nar", "local": "nar",
}


def _present(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "-", "--", "不明")
    if isinstance(value, float):
        return isfinite(value)
    return value not in ([], {})


def _number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
        return n if str(value).strip() == str(n) and n > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def normalize_circuit(value: Any) -> str | None:
    return CIRCUITS.get(str(value or "").strip().lower())


def build_data_status(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Make a small factual observation/coverage record; no hidden scoring."""
    source = detail if isinstance(detail, dict) else {}
    race_id = str(source.get("id") or "")
    circuit = normalize_circuit(source.get("circuit"))
    race_date = date_key(source.get("date"))
    raw_horses = source.get("horses")
    horses = raw_horses if isinstance(raw_horses, list) else []
    missing = Counter()
    warnings: list[str] = []

    for field in RACE_FIELDS:
        if not _present(source.get(field)):
            missing["race." + field] += 1
    if not circuit:
        warnings.append("unknown-circuit")
    if race_id.startswith(("jra-", "nar-")) and circuit:
        if not race_id.startswith(circuit + "-"):
            warnings.append("race-circuit-conflict")
    if not race_date:
        warnings.append("invalid-race-date")
    if not horses:
        warnings.append("no-runner-evidence")

    seen: set[int] = set()
    with_history = 0
    same_or_future = 0
    invalid_history_dates = 0
    observed_prior = 0
    valid_horses = 0

    for horse in horses:
        if not isinstance(horse, dict):
            warnings.append("non-object-runner")
            continue
        valid_horses += 1
        for field in HORSE_FIELDS:
            if not _present(horse.get(field)):
                missing["horse." + field] += 1
        number = _number(horse.get("horseNumber"))
        if number is None:
            warnings.append("invalid-runner-number")
        elif number in seen:
            warnings.append("duplicate-runner-number")
        else:
            seen.add(number)

        for history_field in ("allPastRuns", "recentRaces"):
            raw = horse.get(history_field)
            if not isinstance(raw, list):
                continue
            for run in raw:
                if not isinstance(run, dict):
                    continue
                dt = date_key(run.get("date") or run.get("raceDate") or run.get("日付"))
                if not dt:
                    invalid_history_dates += 1
                elif race_date and dt >= race_date:
                    same_or_future += 1
        prior = merge_career(horse.get("allPastRuns"), horse.get("recentRaces"), race_date)
        with_history += bool(prior)
        observed_prior += len(prior)

    try:
        field_size = int(source.get("fieldSize") or 0)
    except (TypeError, ValueError, OverflowError):
        field_size = 0
    if field_size > 0 and valid_horses > field_size:
        warnings.append("more-runners-than-declared")
    if field_size > 0 and valid_horses < field_size:
        warnings.append("fewer-runners-than-declared")
    if same_or_future:
        warnings.append("non-prior-history-present")
    if invalid_history_dates:
        warnings.append("unusable-history-date")

    return {
        "schema": "arvexq-v3-observed-data-1",
        "raceId": race_id,
        "circuit": circuit,
        "raceDate": race_date or None,
        "status": "observed-partial" if missing or warnings else "observed-unverified",
        "horseCount": valid_horses,
        "reportedFieldSize": field_size or None,
        "runnersWithPriorRuns": with_history,
        "runnersWithoutPriorRuns": valid_horses - with_history,
        "observedPriorRuns": observed_prior,
        "sameOrFutureHistoryRows": same_or_future,
        "invalidHistoryDateRows": invalid_history_dates,
        "missing": dict(sorted(missing.items())),
        "warnings": sorted(set(warnings)),
        "careerCompleteness": "unverified",
    }
