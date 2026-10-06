"""Odds domain helpers."""
from __future__ import annotations

from typing import Any

from arvexq.race_card import horse_number, sorted_horses


def _float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace("倍", "").strip())
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(float(str(value).replace("人気", "").strip()))
    except (TypeError, ValueError):
        return None


def build_odds_snapshot(race: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = []
    for horse in sorted_horses(race):
        odds = _float(horse.get("odds") or horse.get("winOdds") or horse.get("単勝"))
        popularity = _int(horse.get("popularity") or horse.get("rank") or horse.get("人気"))
        rows.append(
            {
                "number": horse_number(horse),
                "name": horse.get("name") or horse.get("horseName") or "",
                "winOdds": odds,
                "popularity": popularity,
                "singleDigit": odds is not None and odds < 10.0,
            }
        )
    return rows


def odds_complete(race: dict[str, Any] | None) -> bool:
    active = [row for row in build_odds_snapshot(race) if row["winOdds"] is not None]
    horses = sorted_horses(race, include_scratched=False)
    return bool(horses) and len(active) >= max(1, len(horses) - 1)


__all__ = ["build_odds_snapshot", "odds_complete"]
