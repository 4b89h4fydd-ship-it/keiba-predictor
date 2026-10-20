"""Describe observed paired archive dates without claiming uninterrupted coverage."""
from datetime import date, timedelta
from pathlib import Path


def calendar_window(days: list[str], *, archive_dir: Path | None = None) -> dict:
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
    def evidence(day: str) -> dict:
        if archive_dir is None:
            presence = "not-checked"
        else:
            name = day + ".json"
            card = (archive_dir / "racecards" / name).is_file()
            manifest = (archive_dir / "saved-snapshots" / name).is_file()
            presence = ("both-present" if card and manifest else
                        "racecard-only" if card else
                        "manifest-only" if manifest else "neither-present")
        return {
            "date": day, "savedPair": "not-selected",
            "filePresence": presence,
            "officialRaceSchedule": "unverified",
            "reason": "no-selected-saved-pair; racing-or-no-racing-unknown",
        }
    return {
        "schema": "arvexq-v3-archive-calendar-window-1",
        "selectedDates": days,
        "selectedSavedDays": len(days),
        "calendarSpanDays": span,
        "missingCalendarDays": missing,
        "missingDayEvidence": [evidence(day) for day in missing],
        "consecutiveCalendarDays": not missing,
        "officialRaceDayCoverageVerified": False,
    }
