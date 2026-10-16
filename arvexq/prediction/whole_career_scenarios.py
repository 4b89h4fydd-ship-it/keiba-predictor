"""Independent whole-career evidence module for the replacement forecast.

Development stage: do not call it a calibrated probability or deploy before tests.
"""
from __future__ import annotations
from collections import Counter
from arvexq.prediction.past_performance import observed_runs

VERSION = "arvexq-whole-career-scenario-v2-dev"

def _num(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None

def analyze_horse(horse, race):
    runs = observed_runs(horse, race, limit=None)
    n = len(runs)
    wins = sum(r["finish"] == 1 for r in runs)
    top2 = sum(r["finish"] <= 2 for r in runs)
    top3 = sum(r["finish"] <= 3 for r in runs)
    distance = _num(race.get("distance") or race.get("distanceM"))
    compatible = []
    styles = Counter()
    advances = 0
    for run in runs:
        d = _num(run.get("distance"))
        if (distance is not None and d is not None and abs(distance-d) <= 150
                and race.get("surface") and run.get("surface") == race.get("surface")):
            compatible.append(run)
        corners = run.get("cornerPositions")
        if not isinstance(corners, list) or not corners:
            continue
        first = _num(corners[0])
        last = _num(corners[-1])
        field = int(run["fieldSize"])
        if first is None or field <= 0:
            continue
        share = first / field
        role = "逃げ" if share <= 0.15 else "先行" if share <= 0.4 else "差し" if share <= 0.75 else "追込"
        styles[role] += 1
        if last is not None and last > run["finish"]:
            advances += 1
    return {
        "horseNumber": horse.get("horseNumber"),
        "name": horse.get("name"),
        "observedStarts": n,
        "winRate": wins/n if n else None,
        "top2Rate": top2/n if n else None,
        "top3Rate": top3/n if n else None,
        "comparableStarts": len(compatible),
        "comparableTop3Rate": (sum(r["finish"] <= 3 for r in compatible)/len(compatible)
                               if compatible else None),
        "observedPositionStyles": dict(styles),
        "observedClosingAdvances": advances,
        "evidenceStatus": "observed" if n else "missing",
    }

def analyze_race(race):
    horses = [h for h in race.get("horses", []) if isinstance(h, dict) and h.get("horseNumber")
              and not h.get("scratched") and not h.get("cancelled")]
    reports = [analyze_horse(h, race) for h in horses]
    lead = sum(r["observedPositionStyles"].get("逃げ", 0) > 0 for r in reports)
    return {"version": VERSION, "horseReports": reports, "possibleLeadContenders": lead,
            "scenario": "先行争い激化の可能性" if lead >= 3 else "隊列が落ち着く可能性",
            "status": "evidence-only-not-production-prediction"}
