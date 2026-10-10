"""全キャリア分析モジュール。

過去5走に制限されず、取得可能な全過去走を分析対象とする。
発走後データは入力に含めないこと。
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

RECENT_WINDOW = 5


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _finish_percentile(run: dict) -> float | None:
    pos = _to_float(run.get("finish_position"))
    size = _to_float(run.get("field_size"))
    if not pos or not size or size < 2:
        return None
    return 1.0 - (pos - 1) / (size - 1)


def _distance_bucket(distance: Any) -> str:
    d = _to_float(distance)
    if d is None:
        return "unknown"
    if d <= 1400:
        return "sprint"
    if d <= 1800:
        return "mile"
    if d <= 2200:
        return "middle"
    return "long"


def _group_stats(runs: list[dict]) -> dict:
    percentiles = [p for p in (_finish_percentile(r) for r in runs) if p is not None]
    wins = sum(1 for r in runs if _to_float(r.get("finish_position")) == 1)
    top3 = sum(1 for r in runs if _to_float(r.get("finish_position")) in (1, 2, 3))
    return {
        "runs": len(runs),
        "win_rate": wins / len(runs) if runs else None,
        "top3_rate": top3 / len(runs) if runs else None,
        "avg_finish_percentile": mean(percentiles) if percentiles else None,
    }


def _aptitude(runs: list[dict], key: str) -> dict:
    groups: dict[Any, list[dict]] = {}
    for run in runs:
        value = run.get(key)
        if key == "distance":
            value = _distance_bucket(value)
        groups.setdefault(value, []).append(run)
    return {str(k): _group_stats(v) for k, v in groups.items()}


def analyze_career(runs: list[dict]) -> dict:
    runs = [r for r in runs if isinstance(r, dict)]
    if not runs:
        return {
            "total_runs": 0,
            "analyzed_runs": 0,
            "recent_runs": [],
            "recent_stats": _group_stats([]),
            "aptitude": {},
            "best_performance": None,
            "consistency": None,
            "representative_runs": [],
            "pace_suitability": {},
            "missing_fields": [],
            "data_limitation": "no_runs",
        }

    ordered = sorted(runs, key=lambda r: str(r.get("date") or ""))
    recent = ordered[-RECENT_WINDOW:]
    percentiles = [p for p in (_finish_percentile(r) for r in ordered) if p is not None]

    best = None
    for run in ordered:
        p = _finish_percentile(run)
        if p is not None and (best is None or p > best["finish_percentile"]):
            best = {
                "date": run.get("date"),
                "distance": run.get("distance"),
                "course_type": run.get("course_type"),
                "track_condition": run.get("track_condition"),
                "finish_position": run.get("finish_position"),
                "finish_percentile": p,
            }

    styles: dict[str, int] = {}
    for run in ordered:
        style = run.get("running_style") or "unknown"
        styles[str(style)] = styles.get(str(style), 0) + 1

    same_condition = [
        r for r in ordered
        if r.get("course_type") == ordered[-1].get("course_type")
        and _distance_bucket(r.get("distance")) == _distance_bucket(ordered[-1].get("distance"))
    ]

    missing = sorted({k for r in ordered for k in ("date", "distance", "course_type", "track_condition", "finish_position", "field_size") if r.get(k) in (None, "")})

    return {
        "total_runs": len(ordered),
        "analyzed_runs": len(ordered),
        "recent_runs": recent,
        "recent_stats": _group_stats(recent),
        "aptitude": {
            "distance": _aptitude(ordered, "distance"),
            "course_type": _aptitude(ordered, "course_type"),
            "track_condition": _aptitude(ordered, "track_condition"),
        },
        "best_performance": best,
        "consistency": 1.0 - pstdev(percentiles) if len(percentiles) > 1 else None,
        "representative_runs": same_condition,
        "pace_suitability": styles,
        "missing_fields": missing,
        "data_limitation": "partial" if missing else "complete",
    }
