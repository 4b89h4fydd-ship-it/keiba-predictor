"""Observed-only six-factor racing evidence. Research-only until sealed backtest.

No missing signal is filled with a neutral score. Historical races must precede
the target race, and unrelated surfaces or circuits are not pooled as equivalent.
"""
from __future__ import annotations
from statistics import mean
from arvexq.prediction.past_performance import observed_runs

def number(value):
    try:
        x = float(value)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None

def text(value):
    return str(value or "").strip().lower().replace("　", "")

def orientation(record):
    for key in ("turnDirection", "direction", "courseDirection", "回り"):
        v = text(record.get(key))
        if v in ("右", "右回り", "right", "r"):
            return "right"
        if v in ("左", "左回り", "left", "l"):
            return "left"
    return None

def margin_seconds(run):
    # Only time-defined fields. Never equate lengths, ranks and seconds.
    return number(run.get("marginSeconds") if run.get("marginSeconds") is not None
                  else run.get("timeBehindWinner"))

def signals(horse, race):
    runs = observed_runs(horse, race, limit=None)
    track = text(race.get("track"))
    surface = text(race.get("surface"))
    distance = number(race.get("distance") or race.get("distanceM"))
    direction = orientation(race)
    matched = []
    recent = runs[:5]
    for run in runs:
        d = number(run.get("distance") or run.get("distanceM"))
        same_track = bool(track and text(run.get("track")) == track)
        same_surface = bool(surface and text(run.get("surface")) == surface)
        same_distance = distance is not None and d is not None and d == distance
        run_direction = orientation(run)
        same_direction = direction is not None and run_direction == direction
        if same_track and same_surface and same_distance and same_direction:
            matched.append(run)
    def top3(rows):
        return sum(int(row["finish"] <= 3) for row in rows) / len(rows) if rows else None
    # Most recent records get highest weights, only among observed dated runs.
    weights = list(range(len(recent), 0, -1))
    recent_top3 = sum(w * (r["finish"] <= 3) for w,r in zip(weights,recent))/sum(weights) if weights else None
    recent_margin_rows = [(w, margin_seconds(r)) for w,r in zip(weights,recent)]
    recent_margin_rows = [(w,m) for w,m in recent_margin_rows if m is not None and m >= 0]
    recent_margin = sum(w*m for w,m in recent_margin_rows)/sum(w for w,_ in recent_margin_rows) if recent_margin_rows else None
    margins = [margin_seconds(r) for r in matched]
    margins = [m for m in margins if m is not None and m >= 0]
    # Rank-position gain records closing strength as a pace signal, not a
    # fabricated horse style classification.
    advances = []
    for r in recent:
        raw = r.get("cornerPositions") or r.get("passing")
        if isinstance(raw, str):
            import re
            positions = [int(x) for x in re.findall(r"\d+",raw)]
        elif isinstance(raw, list):
            positions = [int(x) for x in raw if number(x) is not None]
        else:
            positions = []
        if positions and r["fieldSize"] > 1:
            advances.append((positions[-1]-r["finish"])/(r["fieldSize"]-1))
    return {
        "version":"six-factor-observed-research-v1",
        "historicalStarts":len(runs),
        "exactCourseStarts":len(matched),
        "exactCourseTop3Rate":top3(matched),
        "overallTop3Rate":top3(runs),
        "recentWeightedTop3Rate":recent_top3,
        "recentWeightedMarginSeconds":recent_margin,
        "exactCourseMeanMarginSeconds":mean(margins) if margins else None,
        "recentCornerToFinishGain":mean(advances) if advances else None,
        "courseIdentityComplete":bool(track and surface and distance is not None and direction),
        "marginSamples":len(margins),
        "paceSamples":len(advances),
        "note":"Observed context only; cannot be interpreted as calibrated probabilities",
    }
