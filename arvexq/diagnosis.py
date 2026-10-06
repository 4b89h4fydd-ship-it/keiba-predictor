"""Detailed all-runner diagnosis domain.

Diagnosis explains the prediction; it does not fetch data and does not generate
bets.  Horse detail, including the latest five runs, is embedded per runner.
"""
from __future__ import annotations

from typing import Any

from arvexq.horse_detail import build_horse_detail
from arvexq.race_card import sorted_horses


def _pick(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def diagnose_horse(horse: dict[str, Any], race: dict[str, Any] | None = None) -> dict[str, Any]:
    detail = build_horse_detail(horse, race)
    score = _pick(horse, "overallScore", "totalScore", "score", "総合点")
    grade = _pick(horse, "overallGrade", "grade", "rankGrade", "総合評価") or ""
    mark = _pick(horse, "mark", "predictionMark", "印") or ""
    summary = _pick(horse, "diagnosis", "diagnosisText", "aiComment", "comment", "総評") or ""
    strengths = _text_list(_pick(horse, "strengths", "positiveReasons", "加点材料"))
    risks = _text_list(_pick(horse, "risks", "negativeReasons", "concerns", "不安材料"))
    winning_path = _pick(horse, "winningPath", "winScenario", "勝ち筋") or ""
    return {
        "number": detail["number"],
        "name": detail["name"],
        "mark": mark,
        "grade": grade,
        "score": score,
        "summary": summary,
        "ability": _pick(horse, "abilityGrade", "abilityScore", "ability", "能力評価") or None,
        "record": _pick(horse, "recordGrade", "recordScore", "record", "実績評価") or None,
        "form": _pick(horse, "formGrade", "recentFormScore", "recentForm", "近走評価") or None,
        "paceFit": _pick(horse, "paceFitGrade", "paceFitScore", "paceFit", "展開適性") or None,
        "distanceFit": detail["distanceSuitability"],
        "courseFit": detail["courseSuitability"],
        "goingFit": detail["goingSuitability"],
        "first1f": detail["first1f"],
        "last3f": detail["last3f"],
        "opponentLevel": detail["opponentLevel"],
        "strengths": strengths,
        "risks": risks,
        "winningPath": winning_path,
        "horseDetail": detail,
    }


def build_diagnosis(race: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(race, dict):
        return []
    return [diagnose_horse(horse, race) for horse in sorted_horses(race)]


__all__ = ["build_diagnosis", "diagnose_horse"]
