from __future__ import annotations

from statistics import mean
from typing import Any, Iterable

from arvexq.core.runner_status import is_inactive_runner


def _n(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _runs(h: dict[str, Any]) -> list[dict[str, Any]]:
    rows = h.get("allPastRuns") or h.get("recentRaces") or []
    return [r for r in rows if isinstance(r, dict)][:5]


def _finish_quality(r: dict[str, Any]) -> float:
    finish = _n(r.get("finish"), 99)
    field = max(2.0, _n(r.get("fieldSize"), 12))
    if finish <= 0 or finish >= 99:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (finish - 1.0) / max(1.0, field - 1.0)))


def _speed_raw(r: dict[str, Any]) -> float | None:
    if r.get("speedIndex") is not None:
        return _n(r.get("speedIndex"))
    t = _n(r.get("timeSeconds"))
    d = _n(r.get("distance"))
    return d / t if t > 0 and d > 0 else None


def _relative(vals: list[float | None]) -> list[float]:
    valid = [v for v in vals if v is not None]
    if not valid:
        return [0.5 for _ in vals]
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return [0.5 if v is not None else 0.0 for v in vals]
    return [0.0 if v is None else (v - lo) / (hi - lo) for v in vals]


def horse_evidence(h: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    runs = _runs(h)
    if not runs:
        return {"recent": 0.0, "peak": 0.0, "speed_raw": None, "level": 0.0, "distance": 0.0, "track": 0.0, "condition": 0.0, "stability": 0.0, "sample": 0}

    qualities = [_finish_quality(r) for r in runs]
    weights = [5, 4, 3, 2, 1][: len(qualities)]
    recent = sum(a * b for a, b in zip(qualities, weights)) / sum(weights)
    speeds = [x for x in (_speed_raw(r) for r in runs) if x is not None]
    levels: list[float] = []
    dist_scores: list[float] = []
    track_scores: list[float] = []
    cond_scores: list[float] = []
    target_d = _n(race.get("distance"))
    target_track = race.get("track")
    target_condition = race.get("condition")

    for run, quality in zip(runs, qualities):
        level = run.get("opponentLevel", run.get("levelScore", run.get("racePrize1")))
        if level is not None and _n(level) > 0:
            levels.append(_n(level))
        rd = _n(run.get("distance"))
        diff = abs(rd - target_d) if rd > 0 and target_d > 0 else 9999
        distance_match = 1.0 if diff <= 100 else (0.65 if diff <= 200 else (0.35 if diff <= 400 else 0.0))
        if distance_match:
            dist_scores.append(quality * distance_match)
        if target_track and run.get("track") == target_track:
            track_scores.append(quality)
        if target_condition and run.get("condition") == target_condition:
            cond_scores.append(quality)

    avg = mean(qualities)
    stability = max(0.0, 1.0 - mean(abs(x - avg) for x in qualities)) if len(qualities) >= 2 else qualities[0]
    return {
        "recent": recent,
        "peak": max(qualities),
        "speed_raw": max(speeds) if speeds else None,
        "level": mean(levels) if levels else 0.0,
        "distance": mean(dist_scores) if dist_scores else 0.0,
        "track": mean(track_scores) if track_scores else 0.0,
        "condition": mean(cond_scores) if cond_scores else 0.0,
        "stability": stability,
        "sample": len(runs),
    }


def rank_ability(horses: Iterable[dict[str, Any]], race: dict[str, Any]) -> list[dict[str, Any]]:
    active = [h for h in horses if isinstance(h, dict) and not is_inactive_runner(h)]
    rows = [{"horse": h, "evidence": horse_evidence(h, race)} for h in active]
    if not rows:
        return []

    fields = ["recent", "peak", "level", "distance", "track", "condition", "stability"]
    rel = {k: _relative([r["evidence"][k] if r["evidence"][k] > 0 else None for r in rows]) for k in fields}
    rel["speed"] = _relative([r["evidence"]["speed_raw"] for r in rows])

    for i, row in enumerate(rows):
        components = {k: rel[k][i] for k in ["recent", "peak", "speed", "level", "distance", "track", "condition", "stability"]}
        row["components"] = components
        row["abilityScore"] = round(mean(components.values()) * 100, 1)
        row["evidenceWins"] = sum(v >= 0.67 for v in components.values())
        row["evidenceWeak"] = sum(v <= 0.33 for v in components.values())
        row["sample"] = row["evidence"]["sample"]

    rows.sort(key=lambda r: (-r["abilityScore"], -r["evidenceWins"], r["evidenceWeak"], -r["sample"], int(r["horse"].get("horseNumber") or 999)))
    for idx, row in enumerate(rows, 1):
        row["abilityRank"] = idx
    return rows


def apply_ability_ranking(detail: dict[str, Any]) -> dict[str, Any]:
    horses = detail.get("horses") or []
    ranked = rank_ability(horses, detail)
    by_no = {int(r["horse"].get("horseNumber") or 0): r for r in ranked}
    for h in horses:
        row = by_no.get(int(h.get("horseNumber") or 0))
        if row:
            h["abilityEvidence"] = {
                "rank": row["abilityRank"],
                "score": row["abilityScore"],
                "wins": row["evidenceWins"],
                "weak": row["evidenceWeak"],
                "sample": row["sample"],
                "components": row["components"],
            }
    detail["abilityRanking"] = [
        {
            "horseNumber": int(r["horse"].get("horseNumber") or 0),
            "name": r["horse"].get("name") or "",
            "rank": r["abilityRank"],
            "score": r["abilityScore"],
            "sample": r["sample"],
            "evidenceWins": r["evidenceWins"],
            "evidenceWeak": r["evidenceWeak"],
            "components": r["components"],
        }
        for r in ranked
    ]
    return detail
