#!/usr/bin/env python3
"""Offline JRA/NAR B-model assessment on independently sealed prior fields.

Uses immutable genuine pre-off seal solely as evidence that the card existed
before post time. NEVER feeds original marks/odds/bets into the model.
Uses separately confirmed RESULTS only as labels. Completely research-only.
"""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
import math
from pathlib import Path
from collections import defaultdict

from arvexq.ingest.full_snapshot_codec import unpack_detail
from arvexq.prediction.prerace_archive import sealed_lock
from arvexq.prediction.learned_scenarios import fit_model,predict_model,race_family,active_horses

VERSION="arvexq-sealed-real-world-b-holdout-v1"


def eligible(detail):
    if not isinstance(detail,dict) or not detail.get("id"):
        return None,"invalid-detail"
    try:
        d=unpack_detail(detail)
        if not sealed_lock(d):
            return None,"missing-authentic-preoff-lock"
        result=d.get("result")
        if not isinstance(result,dict) or result.get("status") not in ("確定","confirmed"):
            return None,"non-final-result"
        starters=active_horses(d)
        numbers={int(h["horseNumber"]) for h in starters}
        rows=result.get("finishers") or []
        finishes={int(r["horseNumber"]):int(r["finish"]) for r in rows
                  if isinstance(r,dict) and type(r.get("horseNumber")) is int
                  and type(r.get("finish")) is int}
        if len(finishes)!=len(rows) or numbers!=set(finishes) or sorted(finishes.values())!=list(range(1,len(numbers)+1)):
            return None,"incomplete-or-tied-result"
        if len(numbers)<3 or len(numbers)>24:
            return None,"bad-field-size"
        # No same-race result in ANY inference payload. Historical past runs are
        # date-gated by learned_scenarios.observed_runs.
        if len({str(h.get("name") or "") for h in starters})!=len(starters):
            return None,"ambiguous-horse-identities"
        d["result"]={"status":"確定","finishers":[{"horseNumber":n,"finish":k} for n,k in finishes.items()]}
        return d,""
    except (KeyError,TypeError,ValueError,OverflowError):
        return None,"invalid-evidence"


def _outcomes(model,records):
    points=[]
    errors=defaultdict(int)
    for d in records:
        try:
            labels={x["horseNumber"]:x["finish"] for x in d["result"]["finishers"]}
            input_race=copy.deepcopy(d)
            for key in ("result","results","payouts","preRacePrediction","preRaceBet",
                        "aiEvaluation","honmeiDecision","factorRanking"):
                input_race.pop(key,None)
            analysis=predict_model(input_race,model)
            scenarios=analysis.get("scenarios") or []
            usual=next((s for s in scenarios if s["id"]=="usual"),None)
            if usual is None:
                errors["no-usual-scenario"]+=1
                continue
            dist=usual["probabilities"]
            if set(dist)!=set(labels):
                errors["mismatched-active-field"]+=1
                continue
            winner=next(n for n,rank in labels.items() if rank==1)
            triple=tuple(next(n for n,rank in labels.items() if rank==k)
                         for k in (1,2,3))
            order=usual["orders"]
            orderp={(o["order"][0],o["order"][1],o["order"][2]):o["probability"]
                    for o in order}
            first=[(n,v["win"]) for n,v in dist.items()]
            first.sort(key=lambda row:(-row[1],row[0]))
            top3=sorted(dist,key=lambda n:(-dist[n]["top3"],n))[:3]
            top_order=max(order,key=lambda row:row["probability"])["order"][:3]
            loss=-math.log(max(1e-15,dist[winner]["win"]))
            joint=-math.log(max(1e-15,orderp[triple]))
            points.append({"raceId":d["id"],"date":d["date"],
                           "firstHit":int(first[0][0]==winner),
                           "winnerInTopThree":int(winner in [x[0] for x in first[:3]]),
                           "top3SetHit":int(set(top3)==set(triple)),
                           "exactOrderHit":int(tuple(top_order)==triple),
                           "winnerLogLoss":loss,"orderedTop3LogLoss":joint,
                           "uniformWinnerLogLoss":math.log(len(first))})
        except (ValueError,KeyError,TypeError,ZeroDivisionError,OverflowError) as e:
            errors[type(e).__name__]+=1
    return points,dict(errors)


def _summarize(points):
    if not points:return {"races":0,"status":"no-independent-evaluations"}
    n=len(points)
    keys=("firstHit","winnerInTopThree","top3SetHit","exactOrderHit",
          "winnerLogLoss","orderedTop3LogLoss","uniformWinnerLogLoss")
    result={"races":n,"status":"uncalibrated-research-only"}
    result.update({key:sum(p[key] for p in points)/n for key in keys})
    result["winsOverUniformByLogLoss"]=result["winnerLogLoss"]<result["uniformWinnerLogLoss"]
    return result


def compare_files(paths,*,epochs=35,min_train=40,min_validation=20,min_test=20):
    records=[]
    exclusions=defaultdict(int)
    seen=set()
    for path in paths:
        raw=json.loads(Path(path).read_text(encoding="utf-8"))
        for detail in raw.get("details") or []:
            rid=str(detail.get("id") or "") if isinstance(detail,dict) else ""
            if rid in seen:
                raise ValueError("duplicate historical race ID")
            seen.add(rid)
            d,reason=eligible(detail)
            if d is None:
                exclusions[reason]+=1
            else:
                records.append(d)
    groups=defaultdict(list)
    for race in records:
        groups[(race["circuit"],race_family(race))].append(race)
    reports={}
    for (circuit,family),races in sorted(groups.items()):
        key=f"{circuit}/{family}"
        days=sorted({d["date"] for d in races})
        a=max(2,int(len(days)*.60))
        b=max(a+1,int(len(days)*.80))
        train=[d for d in races if d["date"] in days[:a]]
        validation=[d for d in races if d["date"] in days[a:b]]
        test=[d for d in races if d["date"] in days[b:]]
        rep={"sourceRaces":len(races),"days":len(days),
             "researchSampleMinimumOnly":True,
             "split":{"train":len(train),"validation":len(validation),"test":len(test)},
             "productionEligible":False}
        if (len(days)<5 or len(train)<min_train or len(validation)<min_validation
                or len(test)<min_test):
            rep["status"]="insufficient-independent-chronological-sample"
            reports[key]=rep
            continue
        model=fit_model(train,circuit=circuit,family=family,epochs=epochs)
        v,ve=_outcomes(model,validation)
        t,te=_outcomes(model,test)
        rep.update({"status":"assessed-not-approved",
                    "modelHash":model["modelHash"],
                    "validation":_summarize(v),"test":_summarize(t),
                    "validationExclusions":ve,"testExclusions":te,
                    "trainThrough":model["training"]["lastDate"],
                    "firstValidationDay":min(d["date"] for d in validation),
                    "firstTestDay":min(d["date"] for d in test)})
        reports[key]=rep
    return {"version":VERSION,"totalInputRaces":len(seen),
            "eligibleSealedRaces":len(records),
            "excluded":dict(exclusions),
            "byCircuitAndFamily":reports,
            "claim80PercentAchieved":False,
            "productionEligible":False,
            "note":"No odds, old marks or bets used; result labels never passed to inference."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--in-dir",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--epochs",type=int,default=35)
    args=parser.parse_args()
    files=sorted(Path(args.in_dir).glob("*.json"))
    report=compare_files(files,epochs=args.epochs)
    Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("SEALED_B_REAL_HOLDOUT",json.dumps(report,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
