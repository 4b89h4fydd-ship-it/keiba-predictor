"""Offline fitting and chronological calibration for the new three-analysis model.

Consumes previously fetched, decompressed and explicitly dated ARVEXQ D1 detail
JSON. No new download routes, no edits to D1 and no Stage63/64 imports.
A fitted baseline is NOT certified for live use until separately measured pace
scenario occurrence and historical video-quality gates are satisfied.
"""
from __future__ import annotations
from copy import deepcopy
from math import exp, log
from statistics import mean, pstdev
import json

from .new_method import VERSION, FEATURES, extract, number


def rows_for(races, *, circuit, before=None, after=None, videos=None):
    seen=set()
    for race in sorted(races,key=lambda r:(r.get("date",""),r.get("id",""))):
        if race.get("circuit")!=circuit or (before and race["date"]>=before) or (after and race["date"]<after):
            continue
        rid=race.get("id")
        if not isinstance(rid,str) or rid in seen:
            raise ValueError("missing or duplicate race ID")
        seen.add(rid)
        result=race.get("result") or {}
        if result.get("status")!="確定":
            continue
        detail=deepcopy(race)
        detail.pop("result",None)
        try:
            features=extract(detail,videos=(videos or {}).get(rid))
            labels={int(x["horseNumber"]):int(x["finish"]) for x in result.get("finishers") or []
                    if x.get("horseNumber") is not None and number(x.get("finish")) is not None and number(x["finish"])>=1}
        except (KeyError,TypeError,ValueError):
            continue
        if set(labels)!=set(features) or len(set(labels.values()))!=len(labels):
            continue
        if any(x["form"] is None for x in features.values()):
            continue
        yield rid,race["date"],features,labels


def _sigmoid(z):
    return 1/(1+exp(-max(-40.,min(40.,z))))


def _win_probs(feats, weights, means, temperature):
    scores={}
    for no,row in feats.items():
        scores[no]=sum(weights[k]*(row[k] if row[k] is not None else means[k]) for k in FEATURES)/temperature
    top=max(scores.values())
    vals={n:exp(s-top) for n,s in scores.items()}
    total=sum(vals.values())
    return {n:v/total for n,v in vals.items()}


def train(races, *, circuit, train_before, validate_before, video_by_race=None,
          min_train=15, min_validation=6, iterations=180):
    """Fit pairwise logistic ranking, calibrate winning probabilities separately.

    Only the training set determines imputation/scaling and coefficients.
    Validation never changes horse-level evidence. Test dates are untouched.
    """
    if circuit not in ("中央","地方") or train_before>=validate_before:
        raise ValueError("independent circuit and ordered chronological cutoffs required")
    train_rows=list(rows_for(races,circuit=circuit,before=train_before,videos=video_by_race))
    valid_rows=list(rows_for(races,circuit=circuit,after=train_before,before=validate_before,videos=video_by_race))
    if len(train_rows)<min_train or len(valid_rows)<min_validation:
        raise ValueError("insufficient strictly separated labeled racing data")
    values={k:[] for k in FEATURES}
    for _,_,features,_ in train_rows:
        for row in features.values():
            for k in FEATURES:
                if row[k] is not None:
                    values[k].append(float(row[k]))
    means={k:mean(v) if v else 0.0 for k,v in values.items()}
    scales={k:max(pstdev(v),0.01) if len(v)>1 else 1.0 for k,v in values.items()}
    names=list(FEATURES)
    def vec(row):
        return [(float(row[k] if row[k] is not None else means[k])-means[k])/scales[k] for k in names]
    pairs=[]
    for _,_,features,labels in train_rows:
        vectors={n:vec(row) for n,row in features.items()}
        nums=sorted(labels,key=lambda n:labels[n])
        per=[]
        for i,a in enumerate(nums):
            for b in nums[i+1:]:
                per.append([x-y for x,y in zip(vectors[a],vectors[b])])
        if per:
            pairs.append(per)
    if not pairs:
        raise ValueError("training labels have no ordered pairs")
    coeff=[0.0]*len(names)
    for step in range(iterations):
        grad=[0.0]*len(names)
        for per in pairs:
            for diff in per:
                prob=_sigmoid(sum(w*d for w,d in zip(coeff,diff)))
                error=(prob-1.0)/(len(pairs)*len(per))
                for j,x in enumerate(diff):
                    grad[j]+=error*x
        rate=0.035/(1+step/85.0)
        for j in range(len(coeff)):
            coeff[j]-=rate*(grad[j]+.1*coeff[j])
    weights={k:coeff[i]/scales[k] for i,k in enumerate(names)}
    def nll(temp):
        total=0.0
        for _,_,features,labels in valid_rows:
            probs=_win_probs(features,weights,means,temp)
            winner=min(labels,key=lambda n:labels[n])
            total-=log(max(probs[winner],1.e-15))
        return total/len(valid_rows)
    candidates=[0.45+0.075*i for i in range(95)]
    temperature=min(candidates,key=nll)
    # Scenario pace frequency requires independent measured per-race pace
    # labels. Initial weights are baseline-only and MUST NOT certify racing.
    return {
        "version":VERSION,"circuit":circuit,
        "weights":weights,"featureMeans":means,
        "temperature":temperature,"paceEffect":0.0,
        "scenarioWeights":{"baseline":1.0,"fast":0.0,"slow":0.0},
        "scenarioWeightsValidated":False,
        # No outOfSampleValidated certificate here: only separate untouched
        # future-race validation can authorize that field.
        "missingVideoValidated":all(all(row["video_missing"] == 1.0 for row in f.values())
                                     for _,_,f,_ in train_rows+valid_rows),
        "trainedThrough":max(day for _,day,_,_ in train_rows),
        "calibratedThrough":max(day for _,day,_,_ in valid_rows),
        "trainingRaceCount":len(train_rows),"validationRaceCount":len(valid_rows),
        "validationWinLogLoss":nll(temperature),
        "trainingRaceIds":[rid for rid,_,_,_ in train_rows],
        "validationRaceIds":[rid for rid,_,_,_ in valid_rows],
        "status":"research-model-needs-verified-pace-and-video-acceptance",
    }


def test_holdout(model, races, *, video_by_race=None, quoted_three_way_odds=None):
    """Do not claim ROI without verified pre-off combination quotes and stakes."""
    holdout=list(rows_for(races,circuit=model["circuit"],after=model["calibratedThrough"],
                          videos=video_by_race))
    metrics=[]
    for rid,day,features,labels in holdout:
        if day<=model["calibratedThrough"]:
            continue
        p=_win_probs(features,model["weights"],model["featureMeans"],model["temperature"])
        winner=min(labels,key=lambda n:labels[n])
        lead=max(p,key=p.get)
        lead_finish=labels[lead]
        metrics.append({"raceId":rid,"date":day,"honmeiHorseNumber":lead,
                        "honmeiFinish":lead_finish,
                        "winnerHit":int(lead_finish==1),
                        "top3Hit":int(lead_finish<=3),
                        "winnerLogLoss":-log(max(p[winner],1.e-15)),
                        "winBrier":sum((v-(n==winner))**2 for n,v in p.items())/len(p)})
    if not metrics:
        return {"status":"no-eligible-holdout","raceCount":0,
                "honmeiWinCount":0,"honmeiTop3Count":0,
                "winnerHitRate":None,"honmeiTop3Rate":None,"returnRate":None}
    return {
        "status":"measured-baseline-no-video-claim","raceCount":len(metrics),
        "winnerHitRate":mean(x["winnerHit"] for x in metrics),
        "honmeiWinCount":sum(x["winnerHit"] for x in metrics),
        "honmeiTop3Count":sum(x["top3Hit"] for x in metrics),
        "honmeiTop3Rate":mean(x["top3Hit"] for x in metrics),
        "winnerLogLoss":mean(x["winnerLogLoss"] for x in metrics),
        "winBrier":mean(x["winBrier"] for x in metrics),
        "returnRate":None,
        "reasonNoROI":"cannot evaluate 3連系 return without time-verified pre-off quotes and stake ledger",
        "videoLift":None,"reasonNoVideoLift":"matched verified video tracklets absent",
        "individualRaces":metrics,
    }
