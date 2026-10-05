from __future__ import annotations

from typing import Any


def _horse_no(row: dict[str, Any]) -> int:
    horse = row.get("horse") if isinstance(row.get("horse"), dict) else row
    return int(horse.get("horseNumber") or 0)


def _horse_name(row: dict[str, Any]) -> str:
    horse = row.get("horse") if isinstance(row.get("horse"), dict) else row
    return str(horse.get("name") or "")


def _score(row: dict[str, Any]) -> float:
    return float(row.get("abilityScore", row.get("score", 0.0)) or 0.0)


def build_win_confidence_evidence(ranking: list[dict[str, Any]]) -> dict[str, Any]:
    """Return raw evidence separating the top horse from the runner-up.

    This layer deliberately does not invent a win probability or HIGH/MEDIUM/LOW
    threshold. Calibration belongs to backtest/selection, not prediction core.
    """
    if not ranking:
        return {"available": False, "reason": "no-ranking"}

    top = ranking[0]
    second = ranking[1] if len(ranking) > 1 else None
    top_components = top.get("components") or {}
    second_components = (second or {}).get("components") or {}

    comparisons: dict[str, float] = {}
    top_wins = 0
    second_wins = 0
    ties = 0
    for key in sorted(set(top_components) | set(second_components)):
        a = float(top_components.get(key) or 0.0)
        b = float(second_components.get(key) or 0.0)
        diff = a - b
        comparisons[key] = round(diff, 4)
        if diff > 0:
            top_wins += 1
        elif diff < 0:
            second_wins += 1
        else:
            ties += 1

    return {
        "available": True,
        "horseNumber": _horse_no(top),
        "name": _horse_name(top),
        "runnerUpHorseNumber": _horse_no(second or {}),
        "scoreGap": round(_score(top) - _score(second or {}), 2),
        "componentWins": top_wins,
        "componentLosses": second_wins,
        "componentTies": ties,
        "componentMargins": comparisons,
        "sample": int(top.get("sample") or 0),
        "runnerUpSample": int((second or {}).get("sample") or 0),
        "evidenceWins": int(top.get("evidenceWins") or 0),
        "evidenceWeak": int(top.get("evidenceWeak") or 0),
    }
