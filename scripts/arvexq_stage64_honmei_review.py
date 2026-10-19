#!/usr/bin/env python3
"""◎【単】 and ◎【軸】 first: read-only research summary from saved 527 race validation.

No training on this archive, no production promotion, no ticket-led ranking.
Every result is retrospective and must not be called independent forward proof.
"""
import argparse
import json
import math
from pathlib import Path

ARMS=("baseline","recent5","recent5_shrunk")
METRICS=("winHitRateScored","axisTop3HitRateScored","top3CandidateRecallScored")


def wilson(hits,total,z=1.96):
    if total<=0:return None
    p=hits/total
    base=1+z*z/total
    center=(p+z*z/(2*total))/base
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/base
    return [max(0,center-half),min(1,center+half)]


def report(source):
    if source.get("independentlyVerifiedPreoff") is not False:
        raise ValueError("only explicitly retrospective source accepted")
    circuits=source.get("byCircuit",{})
    if set(circuits)!={"jra","nar"}:
        raise ValueError("missing circuit")
    out={"schema":"arvexq-stage64-honmei-review-v1",
         "validation":"retrospective-used-before-not-heldout",
         "primaryObjective":"winRole/◎【単】 first, axisRole/◎【軸】 second",
         "bettingIsDownstream":True,
         "productionEligible":False,"circuits":{}}
    for owner in ("jra","nar"):
        arms=circuits[owner]
        if set(arms)!=set(ARMS):raise ValueError("ability arms mismatch")
        results={}
        for name in ARMS:
            r=arms[name]
            cohort=r["cohortRaces"];n=r["scoredRaces"]
            if n<=0 or cohort!=n+r["unscoredRaces"]:raise ValueError("cohort mismatch")
            win=r["winnerTop1Hits"];axis=r["axisTop3Hits"];top3=r["winnerTop3Hits"]
            if any(not 0<=v<=n for v in (win,axis,top3)):raise ValueError("bad hit count")
            results[name]={"totalRaces":cohort,"eligible":n,"unscored":cohort-n,
                           "coverage":n/cohort,
                           "winHits":win,"winHitRateScored":win/n,
                           "winHitRateAllRaces":win/cohort,
                           "win95PctWilson":wilson(win,n),
                           "axisTop3Hits":axis,"axisTop3HitRateScored":axis/n,
                           "axisTop3HitRateAllRaces":axis/cohort,
                           "axis95PctWilson":wilson(axis,n),
                           "winnerInFirst3Candidates":top3,"top3CandidateRecallScored":top3/n,
                           "logloss":r.get("meanLogloss"),
                           "brier":r.get("meanBrier")}
        out["circuits"][owner]={"arms":results,
             "highestObservedWinHitArm":max(ARMS,key=lambda x:(results[x]["winHitRateScored"],-ARMS.index(x))),
             "highestObservedAxisHitArm":max(ARMS,key=lambda x:(results[x]["axisTop3HitRateScored"],-ARMS.index(x))),
             "selectionPermitted":False,
             "limitations":["Previously investigated races cannot select a winning arm",
                            "Axis and win predictions are different roles",
                            "Scored-only rate must be displayed alongside total cohort coverage",
                            "New pre-off held-out races needed before deployment"]}
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="docs/research/stage64-results/summary.json")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=report(json.loads(Path(args.input).read_text(encoding="utf-8")))
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({c:{a:{k:round(v["winHitRateScored"]*100,2) for k,v in d["arms"].items()},
                            "axisTop3Pct":{k:round(v["axisTop3HitRateScored"]*100,2) for k,v in d["arms"].items()}}
                      for c,d in result["circuits"].items()},ensure_ascii=False))


if __name__=="__main__":main()
