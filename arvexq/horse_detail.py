"""Horse-detail domain.

The UI exposes horse detail from inside the all-runner diagnosis.  Past five
runs are therefore composed here instead of living in a separate screen.
"""
from __future__ import annotations

from typing import Any

from arvexq.career_analysis import analyze_career
from arvexq.history import all_runs, recent_runs
from arvexq.race_card import horse_number, sorted_horses


def _pick(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _career_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": run.get("date"),
            "distance": run.get("distance"),
            "course_type": run.get("surface"),
            "track_condition": run.get("condition"),
            "finish_position": run.get("finish"),
            "field_size": run.get("fieldSize"),
        }
        for run in runs
    ]


def build_horse_detail(horse: dict[str, Any], race: dict[str, Any] | None = None) -> dict[str, Any]:
    race = race if isinstance(race, dict) else {}
    pedigree = _pick(horse, "pedigree", "blood", "bloodline", "血統")
    if not pedigree:
        pedigree = {
            "sire": _pick(horse, "sire", "father", "父") or "",
            "dam": _pick(horse, "dam", "mother", "母") or "",
            "damsire": _pick(horse, "damsire", "broodmareSire", "母父") or "",
        }
    career = analyze_career(_career_runs(all_runs(horse)))
    return {
        "number": horse_number(horse),
        "name": str(_pick(horse, "name", "horseName", "馬名") or "").strip(),
        "sexAge": _pick(horse, "sexAge", "sex_age", "ageSex", "性齢") or "",
        "bodyWeight": _pick(horse, "bodyWeight", "horseWeight", "馬体重") or "",
        "carriedWeight": _pick(horse, "carriedWeight", "weight", "burdenWeight", "斤量") or "",
        "jockey": _pick(horse, "jockey", "jockeyName", "騎手") or "",
        "trainer": _pick(horse, "trainer", "trainerName", "調教師") or "",
        "prizeMoney": _pick(horse, "prizeMoney", "earnings", "prize", "賞金") or None,
        "runningStyle": _pick(horse, "runningStyle", "style", "脚質") or "",
        "styleRates": _pick(horse, "styleRates", "runningStyleRates", "脚質率") or {},
        "first1f": _pick(horse, "first1f", "first200", "ten1f", "テン1F") or None,
        "last3f": _pick(horse, "last3f", "last600", "上がり") or None,
        "distanceSuitability": _pick(horse, "distanceSuitability", "distanceFit", "距離適性") or None,
        "courseSuitability": _pick(horse, "courseSuitability", "courseFit", "コース適性") or None,
        "goingSuitability": _pick(horse, "goingSuitability", "surfaceSuitability", "馬場適性") or None,
        "opponentLevel": _pick(horse, "opponentLevel", "competitionLevel", "相手レベル") or None,
        "representativeRun": _pick(horse, "representativeRun", "bestRun", "代表走") or None,
        "pedigree": pedigree,
        "recentFive": recent_runs(horse, 5),
        "careerAnalysis": career,
        "raceContext": {
            "track": race.get("track") or race.get("venue") or "",
            "distance": race.get("distance") or race.get("distanceM") or None,
            "surface": race.get("surface") or "",
            "condition": race.get("condition") or race.get("going") or "",
        },
    }


def build_horse_details(race: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(race, dict):
        return []
    return [build_horse_detail(horse, race) for horse in sorted_horses(race)]


__all__ = ["build_horse_detail", "build_horse_details"]