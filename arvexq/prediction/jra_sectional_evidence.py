from __future__ import annotations

from statistics import median
from typing import Any

MODEL_VERSION = "arvexq-jra-sectional-shadow-v1"


def _f(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def run_sectional_percentile(run: dict[str, Any]) -> float | None:
    """Return only a within-race closing-sectional percentile.

    Raw closing seconds are deliberately not compared across races. New JRA result
    parsing stores last3FPercentile directly. Older rows may have a rank and field
    size, in which case the same race-relative transform is reconstructed.
    """
    if not isinstance(run, dict):
        return None
    direct = _f(run.get("last3FPercentile"))
    if direct is not None:
        return _clip01(direct)

    rank = _f(run.get("last3FRank"))
    field = _f(run.get("fieldSize"))
    if rank is None or rank <= 0 or field is None or field < 2 or rank > field:
        return None
    return _clip01(1.0 - (rank - 1.0) / (field - 1.0))


def horse_sectional_evidence(horse: dict[str, Any], race: dict[str, Any] | None = None) -> dict[str, Any]:
    cutoff = str((race or {}).get("date") or "9999-12-31")
    rows = horse.get("allPastRuns") or horse.get("recentRaces") or []
    values: list[float] = []
    recent: list[float] = []

    for run in rows:
        if not isinstance(run, dict):
            continue
        run_date = str(run.get("date") or run.get("raceDate") or "")
        if run_date and run_date >= cutoff:
            continue
        value = run_sectional_percentile(run)
        if value is None:
            continue
        values.append(value)
        if len(recent) < 5:
            recent.append(value)

    trend = None
    if len(recent) >= 2:
        # rows are newest -> oldest; positive means the most recent evidence is better
        trend = recent[0] - median(recent[1:])

    return {
        "modelVersion": MODEL_VERSION,
        "sample": len(values),
        "recentSample": len(recent),
        "median": median(values) if values else None,
        "recentMedian": median(recent) if recent else None,
        "peak": max(values) if values else None,
        "recentPeak": max(recent) if recent else None,
        "recentTrend": trend,
        "rawSecondsUsedForComparison": False,
    }


def attach_jra_sectional_shadow(detail: dict[str, Any]) -> int:
    """Persist shadow evidence only. Never changes marks or four-pillar ranks."""
    if not isinstance(detail, dict) or str(detail.get("circuit") or "") != "中央":
        return 0
    attached = 0
    for horse in detail.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        evidence = horse_sectional_evidence(horse, detail)
        ev = horse.setdefault("integratedEvaluation", {})
        ev["jraSectionalShadow"] = evidence
        if evidence.get("sample"):
            attached += 1
    detail["jraSectionalShadowVersion"] = MODEL_VERSION
    detail["jraSectionalShadowHorseCount"] = attached
    return attached
