"""Research-only margin-led A/B/C/D/E challenger; never a live prediction."""
from __future__ import annotations
from math import exp
import re
from statistics import mean
from arvexq.prediction.past_performance import observed_runs

WEIGHTS = {"A": .35, "B": .25, "C": .20, "D": .15, "E": .05}

def num(value):
    try:
        x = float(value)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None

def observed_positions(run):
    """Use the existing history fields without inventing unavailable corners."""
    raw = run.get("cornerPositions") or run.get("passing")
    if isinstance(raw, (list, tuple)):
        values = [num(v) for v in raw]
    elif isinstance(raw, str) and re.fullmatch(r"\s*\d+(?:\s*[-,→]\s*\d+)+\s*", raw):
        values = [num(v) for v in re.split(r"\s*[-,→]\s*", raw.strip())]
    else:
        return []
    return values if len(values) >= 2 and all(v is not None for v in values) else []


def score(horse, race):
    runs = observed_runs(horse, race, limit=5)
    if not runs:
        return None
    # A: actual winning margin (seconds). Negative values mean the horse won.
    margins = []
    for run in runs:
        v = next((num(run.get(key)) for key in ("marginSeconds", "timeBehindWinner")
                  if num(run.get(key)) is not None), None)
        if v is not None:
            margins.append(exp(-max(0., v)))
    if not margins:
        return None  # Never replace missing winning margins with finish ranks.
    a = sum((len(margins)-i)*v for i,v in enumerate(margins)) / sum(range(1,len(margins)+1))
    # B: opponent-adjusted performance, only where opponent quality is observed.
    ability = []
    for run in runs:
        level = num(run.get("opponentLevel"))
        finish, field = num(run.get("finish")), num(run.get("fieldSize"))
        if (level is not None and 0 <= level <= 1 and finish is not None
                and field is not None and field > 1 and 1 <= finish <= field):
            ability.append(((field-finish)/(field-1))*(.5+.5*level))
    # C: observed course/distance/surface evidence only.
    suitable = []
    for run in runs:
        dist, target = num(run.get("distance")), num(race.get("distance"))
        finish, field = num(run.get("finish")), num(run.get("fieldSize"))
        if (dist is not None and target is not None and abs(dist-target)<=150
                and run.get("surface") and run.get("surface")==race.get("surface")
                and run.get("track")==race.get("track")
                and finish is not None and field is not None and field>1
                and 1 <= finish <= field):
            suitable.append((field-finish)/(field-1))
    # D: recorded corner-position progression; no synthetic pace forecast.
    pace = []
    for run in runs:
        positions = observed_positions(run)
        field = num(run.get("fieldSize"))
        if positions and field is not None and field > 1:
            first,last = num(positions[0]),num(positions[-1])
            if first is not None and last is not None and 1<=first<=field and 1<=last<=field:
                pace.append(.5+(first-last)/(2*(field-1)))
    # E: needs independently validated rider/weight/rest contextual scores.
    # Explicitly unavailable rather than inventing a 50-point neutral score.
    factors = {"A":a, "B":mean(ability) if ability else None,
               "C":mean(suitable) if suitable else None,
               "D":mean(pace) if pace else None, "E":None}
    present = [key for key,v in factors.items() if v is not None]
    if "A" not in present:
        return None
    total = sum(WEIGHTS[key] for key in present)
    return {"score":sum(WEIGHTS[key]*factors[key] for key in present)/total,
            "factors":factors,"coverage":total,"missing":[k for k in WEIGHTS if k not in present],
            "model":"research-margin-abcde-352520155-v1"}
