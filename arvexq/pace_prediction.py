"""Race-development / pace-prediction domain."""
from __future__ import annotations

from typing import Any

from arvexq.race_card import horse_number, sorted_horses

_STAGE_ALIASES = {
    "start": ("start", "スタート"),
    "3c": ("3c", "3C", "thirdCorner", "３Ｃ"),
    "4c": ("4c", "4C", "fourthCorner", "４Ｃ"),
    "stretch": ("stretch", "straight", "直線"),
}


def _stage_value(source: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def build_pace_prediction(race: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(race, dict):
        return {"pace": "", "stages": {}, "runners": []}
    source = race.get("pacePrediction") or race.get("developmentAI") or race.get("paceAI") or {}
    if not isinstance(source, dict):
        source = {}
    stages = {
        canonical: _stage_value(source, aliases)
        for canonical, aliases in _STAGE_ALIASES.items()
    }
    runners = []
    for horse in sorted_horses(race, include_scratched=False):
        runners.append(
            {
                "number": horse_number(horse),
                "name": horse.get("name") or horse.get("horseName") or "",
                "style": horse.get("expectedStyle") or horse.get("runningStyle") or horse.get("style") or "",
                "styleRates": horse.get("styleRates") or horse.get("runningStyleRates") or {},
                "paceFit": horse.get("paceFit") or horse.get("paceFitScore") or horse.get("展開適性") or None,
                "mark": horse.get("mark") or horse.get("印") or "",
            }
        )
    return {
        "pace": source.get("pace") or source.get("scenario") or race.get("pace") or "",
        "frontShare": source.get("frontShare") or race.get("frontShare") or None,
        "stages": stages,
        "runners": runners,
    }


__all__ = ["build_pace_prediction"]
