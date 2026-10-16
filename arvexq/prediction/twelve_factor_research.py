"""Twelve descriptive axes, without arbitrary percentage weights."""
from statistics import mean
from arvexq.prediction.six_factor_research import signals, orientation, number, text
from arvexq.prediction.past_performance import observed_runs

def evidence(horse, race):
    base = signals(horse, race)
    runs = observed_runs(horse, race, limit=None)
    recent = runs[:5]
    track, surface = text(race.get("track")), text(race.get("surface"))
    dist = number(race.get("distance") or race.get("distanceM"))
    direction = orientation(race)
    def group(predicate):
        rows = [r for r in runs if predicate(r)]
        return {"starts":len(rows),"podiumRate":sum(r["finish"]<=3 for r in rows)/len(rows) if rows else None}
    strength = [number(r.get("opponentLevel")) for r in recent]
    strength = [v for v in strength if v is not None and 0<=v<=1]
    axes = {
        "sameTrack":group(lambda r: bool(track and text(r.get("track"))==track)),
        "sameDistance":group(lambda r: dist is not None and number(r.get("distance") or r.get("distanceM"))==dist),
        "sameTurn":group(lambda r: bool(direction and orientation(r)==direction)),
        "sameSurface":group(lambda r: bool(surface and text(r.get("surface"))==surface)),
        "recentForm":{"sample":len(recent),"podiumRate":base["recentWeightedTop3Rate"]},
        "beatenMargin":{"seconds":base["recentWeightedMarginSeconds"],"sample":sum(number(r.get("marginSeconds")) is not None or number(r.get("timeBehindWinner")) is not None for r in recent)},
        "runningStyle":{"cornerGain":base["recentCornerToFinishGain"],"sample":base["paceSamples"]},
        "racePace":{"status":"unavailable-until-opponent-pace-analysis"},
        "podiumStability":{"sample":len(runs),"podiumRate":base["overallTop3Rate"]},
        "opponentStrength":{"sample":len(strength),"meanObserved":mean(strength) if strength else None},
        "winningAbility":{"sample":len(runs),"winRate":sum(r["finish"]==1 for r in runs)/len(runs) if runs else None},
        "crossCircuitTransfer":{"status":"unavailable-until-verified-class-bridge"}
    }
    return {"version":"twelve-factor-observed-research-v1","axes":axes,"exactCourse":base,
            "completeAxes":sum(v.get("status") is None and (v.get("sample",v.get("starts",0)) or 0)>0 for v in axes.values())}
