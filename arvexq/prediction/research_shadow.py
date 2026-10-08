"""Experimental pre-off four-stage pace & ordered-finish shadow.

Only history strictly preceding the race is admissible. Neither odds nor results
for the target race enter this model. Scores and probabilities are UNCALIBRATED:
never use as purchase recommendations or silently replace authoritative marks.
"""
from __future__ import annotations
import hashlib
import json
import math
from statistics import median
from typing import Any

VERSION = "arvexq-research-shadow-v2-distinct-order-roles"


def _number(value: Any) -> float | None:
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _order(run: dict[str, Any]) -> list[int]:
    seq = run.get("cornerPositions")
    if isinstance(seq, list):
        vals = [int(x) for x in (_number(v) for v in seq) if x is not None and 1 <= x <= 30]
        return vals[:4]
    keys = (("corner1","firstCorner","position1"),
            ("corner2","secondCorner","position2"),
            ("corner3","thirdCorner","position3"),
            ("corner4","fourthCorner","position4"))
    vals = []
    for names in keys:
        v = next((_number(run.get(k)) for k in names if _number(run.get(k)) is not None),None)
        if v is not None and 1 <= v <= 30:
            vals.append(int(v))
    return vals


def _past(horse: dict[str, Any], date: str) -> list[dict[str, Any]]:
    runs = horse.get("allPastRuns") or horse.get("recentRaces") or []
    eligible = []
    for r in runs:
        if not isinstance(r,dict):
            continue
        d = str(r.get("date") or r.get("raceDate") or "")[:10]
        # Unknown timestamps are rejected, not assumed to predate the target.
        if not d or len(d)!=10 or d>=date:
            continue
        eligible.append(r)
    eligible.sort(key=lambda r:str(r.get("date") or r.get("raceDate") or ""), reverse=True)
    return eligible[:5]


def _clamp(x: float) -> float:
    return max(0.,min(1.,x))


def _avg(values: list[float]) -> float | None:
    return sum(values)/len(values) if values else None


def horse_evidence(horse: dict[str, Any], race: dict[str, Any]) -> dict[str, Any]:
    """Pace evidence of start/3C/4C/last, not invented corner probabilities."""
    runs = _past(horse,str(race.get("date") or ""))
    starts=[]; thirds=[]; fourths=[]; lasts=[]; gains=[]; front=[]; sectional=[]
    matched_clock=[]; raw_clock=[]
    dist = _number(race.get("distance"))
    going = str(race.get("condition") or race.get("going") or "")
    track = str(race.get("track") or "")
    surface = str(race.get("surface") or "")
    for r in runs:
        field = _number(r.get("fieldSize"))
        pos = _order(r)
        finish = _number(r.get("finish") or r.get("finishPosition") or r.get("rank"))
        if field is not None and field>=2:
            def q(value: int | float) -> float:
                return _clamp(1. - (float(value)-1.)/(field-1.))
            if pos:
                starts.append(q(pos[0]))
                front.append(float(pos[0]<=max(2,int(field*.25))))
            if len(pos)>=3:
                thirds.append(q(pos[-2]))
            if len(pos)>=2:
                fourths.append(q(pos[-1]))
            if finish is not None and 1<=finish<=field:
                lasts.append(q(finish))
                if pos:
                    gains.append(_clamp(.5+(pos[-1]-finish)/(2.*(field-1.))))
        # Historical within-race closing percentile only (no raw 3F comparison).
        v=_number(r.get("last3FPercentile"))
        if v is None:
            rank=_number(r.get("last3FRank"))
            if rank is not None and field is not None and field>=2 and 1<=rank<=field:
                v=1.-(rank-1.)/(field-1.)
        if v is not None:
            sectional.append(_clamp(v))
        seconds=_number(r.get("timeSeconds")); d=_number(r.get("distance"))
        if seconds is not None and seconds>0 and d is not None and d>0:
            speed=d/seconds
            raw_clock.append(speed)
            if (dist is not None and abs(dist-d)<=100 and track and
                str(r.get("track") or "")==track and
                (not surface or str(r.get("surface") or "")==surface) and
                (not going or str(r.get("condition") or r.get("going") or "")==going)):
                matched_clock.append(speed)
    return {
        "historyCount":len(runs),"startPositionStrength":_avg(starts),
        "threeCornerStrength":_avg(thirds),"fourCornerStrength":_avg(fourths),
        "finishStrength":_avg(lasts),"frontStartRate":_avg(front),
        "lastStageGain":_avg(gains),"closingPercentile":_avg(sectional),
        # Compared only among runs of the SAME horse in matching context.
        "matchedClockMedian":median(matched_clock) if len(matched_clock)>=2 else None,
        "matchedClockCount":len(matched_clock),
        "clockAbsoluteNotComparable":True,
        "sampledStages": {"start":len(starts),"3C":len(thirds),"4C":len(fourths),
                          "last":len(lasts)},
    }


def ordered_probabilities(
    weights: list[float], second_weights: list[float] | None = None,
    third_weights: list[float] | None = None,
) -> tuple[list[dict[str,float]],list[dict[str,float]]]:
    """Enumerate stage-role-conditioned ordered finishes (uncalibrated).

    Separate pre-off evidence heads can rank P1, P2 and P3 differently.
    This is a Plackett-Luce-style sequential conditional distribution; no
    fitted Harville exponent is claimed until walk-forward tuning is possible.
    """
    second_weights=weights if second_weights is None else second_weights
    third_weights=weights if third_weights is None else third_weights
    n=len(weights)
    if n<3 or len(second_weights)!=n or len(third_weights)!=n or any(
        not math.isfinite(w) or w<=0 for seq in (weights,second_weights,third_weights) for w in seq
    ):
        return [], []
    total=sum(weights)
    second_total=sum(second_weights);third_total=sum(third_weights)
    p1=[0.]*n;p2=[0.]*n;p3=[0.]*n
    triples=[]
    for i in range(n):
        x=weights[i]/total
        p1[i]=x
        for j in range(n):
            if i==j:continue
            y=second_weights[j]/(second_total-second_weights[i])
            p2[j]+=x*y
            for k in range(n):
                if k==i or k==j:continue
                z=third_weights[k]/(third_total-third_weights[i]-third_weights[j])
                p=x*y*z
                p3[k]+=p
                triples.append({"first":i,"second":j,"third":k,"score":p})
    roles=[{"p1":p1[i],"p2":p2[i],"p3":p3[i],
            "top3":p1[i]+p2[i]+p3[i]} for i in range(n)]
    triples.sort(key=lambda v:-v["score"])
    return roles,triples[:24]


def build_shadow(detail: dict[str, Any]) -> dict[str, Any]:
    """Attach a small immutable shadow to the first genuinely pre-off seal only."""
    from arvexq.core.runner_status import is_inactive_runner
    race_date=str(detail.get("date") or "")
    active=[h for h in detail.get("horses") or []
            if isinstance(h,dict) and not is_inactive_runner(h) and
            int(_number(h.get("horseNumber")) or 0)>0]
    evidence=[horse_evidence(h,detail) for h in active]
    pressure=[e["frontStartRate"] for e in evidence if e["frontStartRate"] is not None]
    credible=sum(e["historyCount"]>=2 and e["sampledStages"]["start"]>=1 for e in evidence)
    min_credible=max(3,math.ceil(.60*len(active)))
    # An arbitrary neutral for a horse lacking any history must never be
    # published as a statistically meaningful order probability.
    sufficient=len(active)>=3 and credible>=min_credible
    lead_count=sum((1 if e["frontStartRate"]>=.6 else 0) for e in evidence
                   if e["frontStartRate"] is not None)
    # Three separate role heads: winning needs start/4C position and finishing,
    # second retains 4C consistency, third emphasises late recovery/closing.
    # All weights are pre-specified experimental priors, NOT learned coefficients.
    role_weights={
        "P1":{"startPositionStrength":.22,"fourCornerStrength":.22,
              "finishStrength":.32,"lastStageGain":.08,"closingPercentile":.16},
        "P2":{"startPositionStrength":.12,"fourCornerStrength":.30,
              "finishStrength":.24,"lastStageGain":.20,"closingPercentile":.14},
        "P3":{"startPositionStrength":.05,"fourCornerStrength":.16,
              "finishStrength":.22,"lastStageGain":.22,"closingPercentile":.35},
    }
    heads={}
    for head,groups in role_weights.items():
        heads[head]=[]
        for evidence_row in evidence:
            weighted=[(evidence_row[k],v) for k,v in groups.items()
                      if evidence_row.get(k) is not None]
            value=sum(score*weight for score,weight in weighted)/sum(
                weight for _,weight in weighted) if weighted else .5
            heads[head].append(math.exp(2.2*(value-.5)))
    roles,triples=ordered_probabilities(heads["P1"],heads["P2"],heads["P3"]) if sufficient else ([],[])
    rows=[{"horseNumber":int(_number(h.get("horseNumber")) or 0),
           "evidence":ev,
           "uncalibrated":{k:round(v,9) for k,v in role.items()} if roles else None}
          for h,ev,role in zip(active,evidence,roles)]
    combos=[{"first":rows[q["first"]]["horseNumber"],
             "second":rows[q["second"]]["horseNumber"],
             "third":rows[q["third"]]["horseNumber"],
             "uncalibratedScore":round(q["score"],9)} for q in triples]
    payload={"version":VERSION,"raceId":str(detail.get("id") or ""),
             "date":race_date,"source":"pre-off historical runs only",
             "mode":"research-only-not-for-betting",
             "evidenceSufficientForShadow":sufficient,
             "evidenceCoverage":{"credibleHorseCount":credible,"minimumCredibleRequired":min_credible,
                                 "eligibleRunnerCount":len(active)},
             "pressure": {"credibleHistoryHorses":len(pressure),
                          "possibleLeadContenders":lead_count,
                          "historicalFrontRateMean":_avg(pressure)},
             "rows":rows,"orderedTrifectaShadow":combos}
    payload["hash"]=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,
                    separators=(",",":"),default=str).encode()).hexdigest()
    return payload
