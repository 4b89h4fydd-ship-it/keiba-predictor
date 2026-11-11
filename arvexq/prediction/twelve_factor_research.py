"""Twelve descriptive axes, without arbitrary percentage weights."""
from statistics import mean
from collections import Counter
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
    # Compare previous running styles among actual entrants rather than inventing
    # a numerical pace from this horse alone.
    styles=[]
    for entrant in race.get("horses") or []:
        past=observed_runs(entrant,race,limit=3)
        fronts=[]
        for prior in past:
            corners=prior.get("cornerPositions") or prior.get("passing")
            if isinstance(corners,str):
                import re
                corners=[int(n) for n in re.findall(r"\\d+",corners)]
            if isinstance(corners,list) and corners:
                try: fronts.append(int(corners[0]))
                except (ValueError,TypeError): pass
        if fronts: styles.append((entrant.get("horseNumber"),sum(p<=3 for p in fronts)/len(fronts)))
    front_count=sum(v>=0.5 for _,v in styles)
    this_front=next((v for n,v in styles if n==horse.get("horseNumber")),None)
    # Source-tagged circuit records; avoid guessing class equivalence.
    circuit=str(race.get("circuit") or "")
    target="JRA" if circuit in ("中央","JRA","central") else "NAR" if circuit in ("地方","NAR","local") else None
    def observed_circuit(run):
        v=str(run.get("circuit") or run.get("organization") or "")
        if v in ("中央","JRA","central"): return "JRA"
        if v in ("地方","NAR","local"): return "NAR"
        return None
    cross=[r for r in runs if target and observed_circuit(r) not in (target,None)]
    same=[r for r in runs if target and observed_circuit(r)==target]
    axes = {
        "sameTrack":group(lambda r: bool(track and text(r.get("track"))==track)),
        "sameDistance":group(lambda r: dist is not None and number(r.get("distance") or r.get("distanceM"))==dist),
        "sameTurn":group(lambda r: bool(direction and orientation(r)==direction)),
        "sameSurface":group(lambda r: bool(surface and text(r.get("surface"))==surface)),
        "recentForm":{"sample":len(recent),"podiumRate":base["recentWeightedTop3Rate"]},
        "beatenMargin":{"seconds":base["recentWeightedMarginSeconds"],"sample":sum(number(r.get("marginSeconds")) is not None or number(r.get("timeBehindWinner")) is not None for r in recent)},
        "runningStyle":{"cornerGain":base["recentCornerToFinishGain"],"sample":base["paceSamples"]},
        "racePace":{"observedFrontRunners":front_count,"entrantStyle":this_front,"sample":len(styles),"status":"observed-context-not-calibrated" if this_front is not None else "missing-historical-corners"},
        "podiumStability":{"sample":len(runs),"podiumRate":base["overallTop3Rate"]},
        "opponentStrength":{"sample":len(strength),"meanObserved":mean(strength) if strength else None},
        "winningAbility":{"sample":len(runs),"winRate":sum(r["finish"]==1 for r in runs)/len(runs) if runs else None},
        "crossCircuitTransfer":{"crossStarts":len(cross),"targetStarts":len(same),"crossPodiumRate":sum(r["finish"]<=3 for r in cross)/len(cross) if cross else None,"targetPodiumRate":sum(r["finish"]<=3 for r in same)/len(same) if same else None,"status":"observed-results-no-class-equivalence" if cross else "no-confirmed-cross-circuit-results"}
    }
    return {"version":"twelve-factor-observed-research-v1","axes":axes,"exactCourse":base,
            "completeAxes":sum(v.get("status") is None and (v.get("sample",v.get("starts",0)) or 0)>0 for v in axes.values())}
