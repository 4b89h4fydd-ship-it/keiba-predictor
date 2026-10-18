"""Independent factual horse identity comparison: no I/O, mutation or prediction.

A JRA/NAR runner may have only one race start on a given race date. This
adapter records the first race ID for each observed horse name, reporting
conflicting race IDs without inferring which source is correct.
"""
from __future__ import annotations


def compare_same_day_runner(
    first_race_by_name: dict[str, str],
    *,
    race_id: str,
    horse_name: object,
    horse_number: object,
) -> dict | None:
    """Return collision evidence or None.

    Input: caller-maintained day-scoped name-to-first-race index.
    Output: a validation error for a cross-race collision only.
    Dependencies: Python stdlib only.
    The index is updated only with an observed first race; records are untouched.
    """
    name = str(horse_name or "").strip()
    if not name:
        return None
    first = first_race_by_name.setdefault(name, race_id)
    if first != race_id:
        return {"raceId": race_id, "otherRaceId": first,
                "horseName": name, "horseNumber": horse_number,
                "error": "same runner name in multiple races on day"}
    return None
