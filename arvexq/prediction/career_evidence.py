"""Race-date-bounded all-career evidence for prediction audits.

Never count same-day or future starts and never assume the most recent five
starts represent career performance. This diagnostic does not overwrite
pre-off decisions or invent missing lifetime races.
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Any


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip().replace("/", "-")
    try:
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def career_rates(horse: dict[str, Any], race_date: str) -> dict[str, Any]:
    limit = _date(race_date)
    rows = horse.get("allPastRuns")
    if not isinstance(rows, list) or limit is None:
        return {"datedStarts": 0, "wins": 0, "top2": 0, "top3": 0,
                "winRate": None, "top2Rate": None, "top3Rate": None,
                "status": "missing-full-dated-history"}
    seen: set[tuple[str, str, str]] = set()
    starts = wins = top2 = top3 = 0
    for run in rows:
        if not isinstance(run, dict):
            continue
        at = _date(run.get("date") or run.get("raceDate"))
        if at is None or at >= limit:
            continue
        try:
            finish = int(run.get("finish") or run.get("finishPosition") or run.get("rank") or 0)
            field = int(run.get("fieldSize") or 0)
        except (TypeError, ValueError):
            continue
        if finish <= 0 or field <= 1 or finish > field:
            continue
        key = (str(at), str(run.get("raceId") or run.get("raceName") or ""),
               str(run.get("track") or run.get("course") or ""))
        if key in seen:
            continue
        seen.add(key)
        starts += 1
        wins += finish == 1
        top2 += finish <= 2
        top3 += finish <= 3
    return {"datedStarts": starts, "wins": wins, "top2": top2, "top3": top3,
            "winRate": wins / starts if starts else None,
            "top2Rate": top2 / starts if starts else None,
            "top3Rate": top3 / starts if starts else None,
            "status": "dated-history-observed" if starts else "missing-full-dated-history"}
