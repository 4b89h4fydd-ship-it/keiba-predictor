"""Day-disjoint holdout experiment for PREOFF 14-factor snapshots; never deploy weights."""
from __future__ import annotations
from itertools import product
from typing import Any

FAMILIES=("ability","record","suitability","support")
VERSION="arvexq-14-factor-temporal-calibration-v1"


def pick(sample:dict[str,Any], weights:tuple[int,int,int,int])->int|None:
    scores=[]
    for row in sample.get("rows") or []:
        family=row.get("families") or {}
        present=[(float(family[k]),w) for k,w in zip(FAMILIES,weights)
                 if isinstance(family.get(k),(int,float)) and w>0]
        denom=sum(w for v,w in present)
        if denom:
            scores.append((sum(v*w for v,w in present)/denom,int(row["horseNumber"])))
    return min(scores,key=lambda z:(-z[0],z[1]))[1] if scores else None


def calibrate(samples:list[dict[str,Any]],min_train:int=80,min_holdout:int=30)->dict[str,Any]:
    unique={}
    for sample in samples:
        if not isinstance(sample,dict) or not sample.get("raceId") or not sample.get("date"):
            continue
        if sample.get("source")!="sealed-hash-verified-preoff-factor-shadow":
            continue
        if len(sample.get("rows") or [])<3:
            continue
        try:
            if int(sample["winner"])<=0:continue
        except (KeyError,ValueError,TypeError):continue
        unique[str(sample["raceId"])]=sample
    rows=sorted(unique.values(),key=lambda z:(z["date"],z["raceId"]))
    dates=sorted(set(s["date"] for s in rows))
    result={"version":VERSION,"eligible":False,"samples":len(rows),
            "candidateOnly":True,"liveModelChange":False,
            "futureRaceOutcomesUsedForTraining":False}
    if len(rows)<min_train+min_holdout or len(dates)<3:
        result["reason"]="insufficient-immutable-history";return result
    split=None
    for date in dates[1:]:
        past=[r for r in rows if r["date"]<date]
        future=[r for r in rows if r["date"]>=date]
        if len(past)>=min_train and len(future)>=min_holdout:
            split=date,past,future
    if split is None:
        result["reason"]="no-day-disjoint-holdout";return result
    date,train,test=split
    possible=[w for w in product(range(5),repeat=4) if sum(w)==4]
    def hits(rows,weights):
        return sum(pick(r,weights)==int(r["winner"]) for r in rows)
    chosen=min(possible,key=lambda w:(-hits(train,w),w))
    baseline=(1,1,1,1)
    candidate=[pick(r,chosen)==int(r["winner"]) for r in test]
    original=[pick(r,baseline)==int(r["winner"]) for r in test]
    improved=sum(c and not b for c,b in zip(candidate,original))
    degraded=sum(b and not c for c,b in zip(candidate,original))
    result.update({"eligible":True,"trainingRaces":len(train),
        "holdoutRaces":len(test),"splitDate":date,
        "experimentalWeights":dict(zip(FAMILIES,[v/4 for v in chosen])),
        "trainObservedHitRate":hits(train,chosen)/len(train),
        "holdoutObservedHitRate":sum(candidate)/len(test),
        "equalWeightHoldoutRate":sum(original)/len(test),
        "holdoutImproved":improved,"holdoutDegraded":degraded,
        "possibleReview":len(test)>=100 and improved-degraded>=5})
    return result
