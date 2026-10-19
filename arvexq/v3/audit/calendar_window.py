"""Describe observed paired archive dates without claiming uninterrupted coverage."""
from datetime import date, timedelta


def calendar_window(days: list[str]) -> dict:
    if not days:
        raise ValueError("empty saved archive date window")
    parsed = [date.fromisoformat(day) for day in days]
    if any(day.isoformat() != raw for day, raw in zip(parsed, days)):
        raise ValueError("noncanonical saved archive date")
    if len(set(parsed)) != len(parsed) or parsed != sorted(parsed):
        raise ValueError("duplicate or unordered saved archive dates")
    span = (parsed[-1] - parsed[0]).days + 1
    selected = set(parsed)
    missing = [(parsed[0] + timedelta(days=n)).isoformat()
               for n in range(span) if parsed[0] + timedelta(days=n) not in selected]
    return {
        "schema": "arvexq-v3-archive-calendar-window-1",
        "selectedDates": days,
        "selectedSavedDays": len(days),
        "calendarSpanDays": span,
        "missingCalendarDays": missing,
        "missingDayEvidence": [
            {"date": day, "savedPair": "not-selected",
             "officialRaceSchedule": "unverified",
             "reason": "no-selected-saved-pair; racing-or-no-racing-unknown"}
            for day in missing
        ],
        "consecutiveCalendarDays": not missing,
        "officialRaceDayCoverageVerified": False,
    }
