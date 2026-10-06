"""Race-card domain helpers.

This module owns the display-neutral runner list.  Fetching, prediction and UI
formatting stay outside this boundary.
"""
from __future__ import annotations

from typing import Any


def horse_number(horse: dict[str, Any]) -> int:
    for key in ("number", "horseNumber", "umaban", "no", "馬番"):
        try:
            value = int(horse.get(key) or 0)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return 999


def is_scratched(horse: dict[str, Any]) -> bool:
    if bool(horse.get("scratched") or horse.get("withdrawn") or horse.get("isScratched")):
        return True
    status = str(horse.get("status") or horse.get("runnerStatus") or "").strip()
    return status in {"取消", "除外", "競走除外", "出走取消", "競走中止"}


def sorted_horses(detail: dict[str, Any] | None, *, include_scratched: bool = True) -> list[dict[str, Any]]:
    if not isinstance(detail, dict):
        return []
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    if not include_scratched:
        horses = [h for h in horses if not is_scratched(h)]
    return sorted(horses, key=horse_number)


def build_race_card(detail: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for horse in sorted_horses(detail):
        rows.append(
            {
                "number": horse_number(horse),
                "name": str(horse.get("name") or horse.get("horseName") or "").strip(),
                "sexAge": horse.get("sexAge") or horse.get("sex_age") or horse.get("ageSex") or "",
                "bodyWeight": horse.get("bodyWeight") or horse.get("horseWeight") or horse.get("weightBody") or "",
                "carriedWeight": horse.get("carriedWeight") or horse.get("weight") or horse.get("burdenWeight") or "",
                "jockey": horse.get("jockey") or horse.get("jockeyName") or "",
                "trainer": horse.get("trainer") or horse.get("trainerName") or "",
                "style": horse.get("runningStyle") or horse.get("style") or horse.get("脚質") or "",
                "odds": horse.get("odds") or horse.get("winOdds") or horse.get("単勝") or None,
                "popularity": horse.get("popularity") or horse.get("rank") or horse.get("人気") or None,
                "mark": horse.get("mark") or horse.get("印") or "",
                "score": horse.get("overallScore") or horse.get("score") or horse.get("総合点") or None,
                "grade": horse.get("overallGrade") or horse.get("grade") or horse.get("総合評価") or "",
                "scratched": is_scratched(horse),
            }
        )
    return rows


__all__ = ["build_race_card", "horse_number", "is_scratched", "sorted_horses"]
