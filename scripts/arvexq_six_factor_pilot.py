"""Research-only comparison: current live ranker versus observed six-factor role ordering.

Retrospective API race details can contain post-off mutations. This is a
diagnostic screening experiment, NEVER evidence of locked pre-off accuracy.
No score weights are fitted to outcomes or published to the live model.
"""
from __future__ import annotations
import argparse
import copy
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import permutations

from arvexq.prediction.observed_model import rank_observed
from arvexq.prediction.twelve_factor_research import evidence
from scripts.arvexq_current_prediction_audit import finish_order, scrub_for_replay, mark_rows, lock_rank

def _highest(v):
    return float(v) if v is not None else -999.0

def _lowest(v):
    return -float(v) if v is not None else -999.0

def six_order(detail):
    """Field-relative consensus across all observable axes; no priority cascade.

    A missing measurement abstains. One course match cannot veto the other
    evidence. Race-pace and transfers remain explicit missing until verified.
    """
    rows=[]
    for horse in detail.get("horses") or []:
        try:
            n=int(horse.get("horseNumber") or 0)
        except (ValueError,TypeError):
            continue
        if n<=0 or str(horse.get("status") or "") in ("取消","除外"):
            continue
        ev=evidence(horse,detail)
        axes=ev["axes"]
        values={
            "sameTrack":axes["sameTrack"]["podiumRate"] if axes["sameTrack"]["starts"]>=2 else None,
            "sameDistance":axes["sameDistance"]["podiumRate"] if axes["sameDistance"]["starts"]>=2 else None,
            "sameTurn":axes["sameTurn"]["podiumRate"] if axes["sameTurn"]["starts"]>=2 else None,
            "sameSurface":axes["sameSurface"]["podiumRate"] if axes["sameSurface"]["starts"]>=2 else None,
            "recentForm":axes["recentForm"]["podiumRate"],
            "beatenMargin":-axes["beatenMargin"]["seconds"] if axes["beatenMargin"]["seconds"] is not None else None,
            "runningStyle":axes["runningStyle"]["cornerGain"],
            "racePace":(-abs(axes["racePace"]["entrantStyle"]-(0.25 if axes["racePace"]["observedFrontRunners"]>=3 else 0.75)) if axes["racePace"].get("entrantStyle") is not None else None),
            "podiumStability":axes["podiumStability"]["podiumRate"],
            "opponentStrength":axes["opponentStrength"]["meanObserved"],
            "winningAbility":axes["winningAbility"]["winRate"],
            "crossCircuitTransfer":axes["crossCircuitTransfer"]["targetPodiumRate"] if axes["crossCircuitTransfer"]["targetStarts"]>=2 else None,
        }
        rows.append((n,values,ev))
    # Compare horses on each available dimension before combining relative
    # rankings. Contributions are counted once per distinct observable axis.
    strengths={n:[] for n,_,_ in rows}
    names=list(rows[0][1]) if rows else []
    for key in names:
        present=[(n,v[key]) for n,v,_ in rows if v[key] is not None]
        if len(present)<2:
            continue
        for n,value in present:
            wins=sum(value>other for other_n,other in present if other_n!=n)
            ties=sum(value==other for other_n,other in present if other_n!=n)
            strengths[n].append((wins+.5*ties)/(len(present)-1))
    ranking=sorted(rows,key=lambda item:(
        -(sum(strengths[item[0]])/len(strengths[item[0]]) if strengths[item[0]] else -1),
        -len(strengths[item[0]]),item[0]))
    return [n for n,_,_ in ranking],{n:ev for n,_,ev in ranking},{n:len(strengths[n]) for n,_,_ in ranking}

def tickets(rank):
    """Fixed 10-ticket research envelope across top five, not tuned to outcome."""
    head = rank[:5]
    if len(head)<3:
        return []
    return list(permutations(head[:3],3))[:6] + [
        (head[0],head[1],head[3]), (head[1],head[0],head[3]),
        (head[0],head[2],head[3]), (head[0],head[1],head[4])
    ] if len(head)>=5 else list(permutations(head,3))[:10]

def ingest(detail, metrics, exclusions, records):
    actual=finish_order(detail)
    if len(actual)<3:
        exclusions["incomplete-result"]+=1
        return
    clean=scrub_for_replay(copy.deepcopy(detail),str(detail.get("date") or ""))
    try:
        ranking, ev, coverage=six_order(clean)
    except Exception as exc:
        exclusions["compute-error:"+type(exc).__name__]+=1
        return
    if len(ranking)<5:
        exclusions["fewer-than-five-runners"]+=1
        return
    if not any(coverage.values()):
        exclusions["no-comparable-feature-evidence"]+=1
        return
    circuit="JRA" if str(detail.get("circuit") or "") in ("中央","JRA","central") else "NAR"
    predicted=tickets(ranking)
    finish=tuple(actual[:3])
    hit=finish in predicted
    m=metrics[circuit]["newV3Research"]
    m["races"]+=1
    m["winnerTop1"]+=int(ranking[0]==finish[0])
    m["winnerTop3"]+=int(finish[0] in ranking[:3])
    m["trifecta10Hits"]+=int(hit)
    m["ticketPoints"]+=len(predicted)
    records.append({"date":str(detail.get("date") or ""),"raceId":str(detail.get("id") or ""),
        "circuit":circuit,"track":str(detail.get("track") or ""),
        "raceNumber":detail.get("raceNumber"),"rankedTop5":ranking[:5],
        "tickets":[list(v) for v in predicted],"actualTop3":list(finish),
        "trifectaHit":hit,"predictedWinnerHit":ranking[0]==finish[0]})
    exclusions["evaluated"]+=1

def fetch_full(base, race_id):
    url=base.rstrip("/")+"/api/race/"+urllib.parse.quote(str(race_id),safe="")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ARVEXQ-v3-full-race-audit/1"}),timeout=60) as response:
        data=json.load(response)
    return data.get("detail") if isinstance(data.get("detail"),dict) else None

def fetch(base, day):
    url=base.rstrip("/")+"/api/day?"+urllib.parse.urlencode({"date":day,"details":"1"})
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ARVEXQ-six-factor-pilot/1"}),timeout=60) as response:
        return json.load(response).get("details") or []

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input")
    p.add_argument("--days",type=int,default=7)
    p.add_argument("--end-date",default="2026-10-15")
    p.add_argument("--api-base",default="https://kraiz-api.4b89h4fydd.workers.dev")
    p.add_argument("--output",required=True)
    p.add_argument("--full-per-circuit",type=int,default=30)
    args=p.parse_args()
    if not 1<=args.days<=30: p.error("days must be 1..30")
    detail=[]
    if args.input:
        with open(args.input,encoding="utf8") as stream:
            detail=json.load(stream)["details"]
    else:
        end=date.fromisoformat(args.end_date)
        for i in range(args.days):
            dt=str(end-timedelta(days=i))
            day=fetch(args.api_base,dt)
            detail+=day
            print("DAY",dt,"details",len(day),flush=True)
    # /api/day is a compact listing that omits historical arrays.
    # Always load /api/race/{id} to recover archived original observations.
    picked={"JRA":0,"NAR":0}
    restored=[]
    retrieval=Counter()
    for row in detail:
        if not isinstance(row,dict):
            continue
        circuit="JRA" if str(row.get("circuit") or "") in ("中央","JRA","central") else "NAR"
        if picked[circuit]>=args.full_per_circuit:
            continue
        try:
            full=fetch_full(args.api_base,row.get("id"))
        except Exception as exc:
            retrieval["fetch-error:"+type(exc).__name__]+=1
            continue
        if full is None:
            retrieval["missing-full-snapshot"]+=1
            continue
        horses=full.get("horses") or []
        has_history=any(isinstance(h,dict) and (
            h.get("recentRaces") or h.get("allPastRuns") or h.get("careerArchive"))
            for h in horses)
        if not has_history:
            retrieval["full-snapshot-no-history"]+=1
            continue
        restored.append(full)
        picked[circuit]+=1
    detail=restored
    print("FULL_SNAPSHOT",dict(picked),dict(retrieval),flush=True)
    metrics=defaultdict(lambda: defaultdict(lambda:Counter()))
    exclusions=Counter()
    records=[]
    diagnostics=[]
    for row in detail:
        if isinstance(row,dict):
            if len(diagnostics)<5:
                horses=row.get("horses") or []
                first=horses[0] if horses else {}
                diagnostics.append({"raceId":row.get("id"),"date":row.get("date"),
                    "raceKeys":list(row.keys()),"horseCount":len(horses),
                    "firstHorseKeys":list(first.keys()) if isinstance(first,dict) else [],
                    "historyCounts":{k:len(first.get(k) or []) for k in ("recentRaces","allPastRuns","history","runs","pastRaces") if isinstance(first,dict)},
                    "firstHorseNumber":first.get("horseNumber") if isinstance(first,dict) else None})
            ingest(row,metrics,exclusions,records)
    report={"version":"v3-new-model-only-retrospective-v1",
            "warning":"RETROSPECTIVE ONLY: race details may contain updated pre-off features and are not genuine frozen inputs; 10-ticket construction is an arbitrary identical comparison envelope, not an optimized product bet.",
            "receivedDetails":len(detail),"fullSnapshotRetrieval":dict(retrieval),"coverage":dict(exclusions),"byCircuit":{},"inputDiagnostics":diagnostics,"raceResults":records}
    for circuit, variants in metrics.items():
        report["byCircuit"][circuit]={}
        for name, m in variants.items():
            n=m["races"]
            report["byCircuit"][circuit][name]={**dict(m),"winnerTop1Rate":m["winnerTop1"]/n,
                "winnerTop3Rate":m["winnerTop3"]/n,"trifecta10HitRate":m["trifecta10Hits"]/n}
    with open(args.output,"w",encoding="utf8") as output:
        json.dump(report,output,ensure_ascii=False,indent=2)
    print("RESULT="+json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
