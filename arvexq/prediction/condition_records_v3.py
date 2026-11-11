"""Observed, non-imputed horse record splits for the v3 prediction research.

All reported rates are raw official-result ratios, never model probabilities.
Every row is taken from the horse's recorded past starts before race date.
"""
from __future__ import annotations
from arvexq.prediction.past_performance import observed_runs, _number
from arvexq.prediction.six_factor_research import orientation

def _clean(value):
    return str(value or "").strip()

def _stats(rows):
    n=len(rows)
    wins=sum(int(r["finish"])==1 for r in rows)
    top2=sum(int(r["finish"])<=2 for r in rows)
    top3=sum(int(r["finish"])<=3 for r in rows)
    return {"starts":n,"wins":wins,"top2":top2,"top3":top3,
            "winRate":wins/n if n else None,"top2Rate":top2/n if n else None,
            "top3Rate":top3/n if n else None}

def record_splits(horse, race):
    runs=observed_runs(horse,race,limit=None)
    distance=_number(race.get("distance") if race.get("distance") is not None else race.get("distanceM"))
    track=_clean(race.get("track"))
    surface=_clean(race.get("surface"))
    going=_clean(race.get("condition") or race.get("going"))
    turn=orientation(race)
    def rd(r):
        v=r.get("distance")
        return _number(v if v is not None else r.get("distanceM"))
    def oktrack(r): return bool(track and _clean(r.get("track"))==track)
    def okdist(r): return distance is not None and rd(r)==distance
    def oksurface(r): return bool(surface and _clean(r.get("surface"))==surface)
    def okturn(r): return bool(turn and orientation(r)==turn)
    def okgoing(r): return bool(going and _clean(r.get("condition") or r.get("going"))==going)
    buckets={
        "career":runs,
        "last5":runs[:5],
        "last10":runs[:10],
        "sameTrack":[r for r in runs if oktrack(r)],
        "sameDistance":[r for r in runs if okdist(r)],
        "sameSurface":[r for r in runs if oksurface(r)],
        "sameTurn":[r for r in runs if okturn(r)],
        "sameGoing":[r for r in runs if okgoing(r)],
        "trackDistance":[r for r in runs if oktrack(r) and okdist(r)],
        "trackDistanceSurface":[r for r in runs if oktrack(r) and okdist(r) and oksurface(r)],
        "exactCourse":[r for r in runs if oktrack(r) and okdist(r) and oksurface(r) and okturn(r)],
        "distanceExtension":[r for r in runs if rd(r) is not None and distance is not None and rd(r)<distance],
        "distanceShortening":[r for r in runs if rd(r) is not None and distance is not None and rd(r)>distance],
    }
    return {"version":"arvexq-v3-raw-condition-record-v1",
            "observedPastStarts":len(runs),
            "splits":{key:_stats(rows) for key,rows in buckets.items()},
            "status":"observed-only-no-pseudo-probabilities"}
