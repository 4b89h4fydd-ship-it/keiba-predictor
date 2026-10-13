"""Experimental 21-signal pre-off scorer. Not wired to live predictions until parity/backtests pass."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any

VERSION = "arvexq-21-factor-candidate-v01"
AXES = {
    "true_run": (0.45, (
        ("finish_margin", .20), ("opponent_class_recent", .20), ("clock_recent", .20),
        ("race_pressure", .15), ("form_trend", .15), ("documented_trouble", .05),
        ("rest_condition", .05))),
    "pure": (0.35, (
        ("speed_index", .25), ("career_ability", .20), ("career_class", .15),
        ("distance_fit", .15), ("course_fit", .10), ("going_fit", .10),
        ("pedigree_fit", .05))),
    "sectional": (0.20, (
        ("early_position", .20), ("pace_resilience", .20), ("finish_section", .20),
        ("late_progress", .15), ("front_hold", .10), ("course_style", .10),
        ("jockey_style", .05))),
}

def number(x: Any) -> float | None:
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else None
    except (ValueError, TypeError):
        return None

def unit(x: Any) -> float | None:
    v = number(x)
    return None if v is None else max(0., min(1., v))

def avg(values: list[float | None]) -> float | None:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None

def quality(run: dict) -> float | None:
    f, size = number(run.get("finish") or run.get("finishPosition")), number(run.get("fieldSize"))
    return unit((size - f) / (size - 1)) if f is not None and size is not None and size >= 2 and 1 <= f <= size else None

def historical(h: dict, race: dict) -> list[dict]:
    cutoff = str(race.get("date") or "")
    if not cutoff or len(cutoff) != 10:
        return []
    all_runs = (h.get("allPastRuns") or []) + (h.get("recentRaces") or [])
    seen, result = set(), []
    for run in sorted(all_runs, key=lambda r: str(r.get("date") or r.get("raceDate") or ""), reverse=True):
        d = str(run.get("date") or run.get("raceDate") or "")[:10]
        key = (str(run.get("raceId") or ""), d, str(run.get("track") or ""), str(run.get("raceNumber") or ""))
        if not d or d >= cutoff or key in seen or quality(run) is None:
            continue
        seen.add(key)
        result.append(run)
    return result

def scored(h: dict, race: dict) -> dict:
    runs = historical(h, race)
    recent = runs[:5]
    q = [quality(r) for r in recent]
    allq = [quality(r) for r in runs]
    track, dist = str(race.get("track") or ""), number(race.get("distance"))
    going = str(race.get("condition") or race.get("going") or "")
    def hist_fit(pred):
        values = [quality(r) for r in runs if pred(r)]
        return avg(values) if len(values) >= 2 else None
    def relative_corner(run, first=True):
        ps = run.get("cornerPositions") or []
        size = number(run.get("fieldSize"))
        p = number(ps[0] if first else ps[-1]) if ps else None
        return unit((size-p)/(size-1)) if size and size > 1 and p else None
    early = [relative_corner(r) for r in recent]
    late = [relative_corner(r, False) for r in recent]
    closes = []
    for r in recent:
        rank, field = number(r.get("last3fRank") or r.get("last600Rank")), number(r.get("fieldSize"))
        closes.append(unit((field-rank)/(field-1)) if rank and field and field > 1 else unit(r.get("last3fPercentile")))
    # Only published normalized indexes are comparable. Raw seconds are not.
    speed = [number(r.get("speedIndex")) for r in runs]
    speed = [s for s in speed if s is not None]
    # Speed index calibration is not yet source-verified: do not invent a mapping.
    speeds = None
    if speed and all(0 <= s <= 1 for s in speed):
        speeds = avg(sorted(speed, reverse=True)[:3])
    class_recent = [unit(r.get("opponentLevel")) for r in recent]
    class_long = [unit(r.get("opponentLevel")) for r in runs[5:]]
    positions = [(a,b) for a,b in zip(early,late) if a is not None and b is not None]
    moves = [unit(.5 + (b-a)) for a,b in positions]
    front = [(a,b) for a,b in positions if a >= .65]
    trends = None
    if len(q) >= 4 and all(v is not None for v in q):
        trends = unit(.5 + avg(q[:2]) - avg(q[2:]))
    facts = {
        "finish_margin": avg(q),  # No verified margins -> positional quality, documented as partial.
        "opponent_class_recent": avg(class_recent),
        "clock_recent": None,  # Requires course/going-adjusted reference clocks.
        "race_pressure": None,  # Requires published race pace/sectional splits.
        "form_trend": trends,
        "documented_trouble": None,
        "rest_condition": None,
        "speed_index": speeds,
        "career_ability": avg(allq[5:]) if len(allq) > 5 else None,
        "career_class": avg(class_long),
        "distance_fit": hist_fit(lambda r: dist is not None and number(r.get("distance")) is not None and abs(number(r["distance"])-dist)<=100),
        "course_fit": hist_fit(lambda r: track and str(r.get("track") or "") == track),
        "going_fit": hist_fit(lambda r: going and str(r.get("condition") or r.get("going") or "") == going),
        "pedigree_fit": unit((h.get("precomputedMetrics") or {}).get("pedigreeFit")),
        "early_position": avg(early),
        "pace_resilience": None,
        "finish_section": avg(closes),
        "late_progress": avg(moves),
        "front_hold": avg([b for a,b in front]),
        "course_style": None,
        "jockey_style": None,
    }
    axes = {}
    for name,(weight,metrics) in AXES.items():
        known = [(w,facts[k]) for k,w in metrics if facts[k] is not None]
        cover = sum(w for w,_ in known)
        axes[name] = {
            "value": (sum(w*v for w,v in known)/cover if abs(cover-1.0) < 1e-9 else None),
            "coverage": round(cover, 4),
            "weight": weight,
            "signals": {k: {"value": facts[k], "weight":w} for k,w in metrics},
        }
    total = sum(x["weight"]*x["value"] for x in axes.values() if x["value"] is not None)
    included = sum(x["weight"] for x in axes.values() if x["value"] is not None)
    # Avoid presenting an unobserved model fraction as real score.
    return {"version": VERSION, "horseNumber":h.get("horseNumber"),"axes":axes,
            "score": round(100*total, 2) if abs(included-1.0)<1e-9 else None,
            "overallCoverage": round(sum(x["coverage"]*x["weight"] for x in axes.values()),4),
            "status":"candidate-complete" if abs(included-1.0)<1e-9 else "insufficient-evidence",
            "preoffRuns":len(runs), "notCalibrated":True}
