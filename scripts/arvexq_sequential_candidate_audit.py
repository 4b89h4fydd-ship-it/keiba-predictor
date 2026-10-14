#!/usr/bin/env python3
"""Compare research scores on the SAME final races; retrospective, not pre-off proof."""
import json
import math
import base64
import gzip
import hashlib
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
from scripts.arvexq_current_prediction_audit import api_json,finish_order,scrub_for_replay
from arvexq.prediction.factor_model import rank_factor_model
from arvexq.research.sequential_challengers import candidates
from arvexq.research.margin_abcde_candidate import score as margin_abcde_score, num
from arvexq.prediction.past_performance import observed_runs
from arvexq.research.mineta_position_proxy import position_proxy
from arvexq.research.mineta_field_proxy import score_race as mineta_field_scores

def summarize_five(five):
    chosen=five[:5]
    labels={
        "mineta_field_proxy":"Mineta observable-position proxy only",
        "mineta_current_60_40":"Mineta 60% + current 40%",
        "mineta_margin_60_40":"Mineta 60% + margin-focused 40%",
        "mineta_current_margin_60_20_20":"Mineta 60% + current 20% + margin-focused 20%",
    }
    comparison={}
    for name,label in labels.items():
        comparable=[]
        for race in chosen:
            forecast=(race.get("mixedForecasts") or {}).get(name) or {}
            if isinstance(forecast.get("winnerRank"),int) and forecast.get("winnerRank")>0:
                comparable.append((race,forecast))
        hits=sum(x["winnerRank"]==1 for _,x in comparable)
        top3=sum(x["winnerRank"]<=3 for _,x in comparable)
        comparison[name]={
            "label":label,"eligible":len(comparable),"fiveRaceCount":len(chosen),
            "top1Hits":hits,"winnerTop3Hits":top3,
            "top1Rate":round(hits/len(comparable),6) if comparable else None,
            "winnerTop3Rate":round(top3/len(comparable),6) if comparable else None,
            "completeSameFive":len(comparable)==5 and len(chosen)==5,
            "byCircuit":{c:{
                "eligible":sum(r["circuit"]==c for r,_ in comparable),
                "top1Hits":sum(r["circuit"]==c and x["winnerRank"]==1 for r,x in comparable)
            } for c in ("中央","地方")},
        }
    shared=[r for r in chosen if all(
        (r.get("mixedForecasts") or {}).get(name,{}).get("winnerRank") is not None
        for name in labels)]
    same_five={
        "races":len(chosen),"fullyComparableRaces":len(shared),
        "allThreeCombinationsComparableOnFive":len(chosen)==5 and len(shared)==5,
        "labels":labels,
        "missingMethodCount":{k:5-v["eligible"] for k,v in comparison.items()},
        "warning":"No evidence-free margins or positions are invented; unavailable means untested, not a loss.",
    }
    return comparison, same_five


def evaluate():
    results=defaultdict(lambda: {"races":0,"top1":0,"top3":0,"logLossSum":0.})
    coverage=defaultdict(int)
    evidence=defaultdict(lambda: defaultdict(int))
    pilot=[]
    outcomes={}
    for offset in range(7):
        day=(date(2026,10,7)+timedelta(days=offset)).isoformat()
        data=api_json("https://kraiz-api.4b89h4fydd.workers.dev/api/day?date="+day+"&details=1")
        for detail in data.get("details") or []:
            order=finish_order(detail)
            if len(order)>=3:
                outcomes[(str(detail.get("date")),str(detail.get("id")))]=order
    envelopes=0
    for path in sorted(Path("arvexq/ui/static/saved-snapshots").glob("*.json")):
        envelope=json.loads(path.read_text())
        if "gzipBase64" not in envelope: continue
        raw=gzip.decompress(base64.b64decode(envelope["gzipBase64"]))
        if hashlib.sha256(raw).hexdigest()!=envelope.get("sha256"):
            raise ValueError("snapshot hash mismatch")
        detail=json.loads(raw)
        envelopes+=1
        order=outcomes.get((str(detail.get("date")),str(detail.get("id"))))
        if not order: continue
        rows=rank_factor_model(detail.get("horses") or [],detail)
        if len(rows)<3: continue
        variants={"current":{int(z["horse"]["horseNumber"]):z["score"] for z in rows}}
        circuit = "中央" if str(detail.get("circuit") or "") in ("中央","JRA") else "地方" if str(detail.get("circuit") or "") in ("地方","NAR") else "不明"
        for z in rows:
            n=int(z["horse"]["horseNumber"])
            ev=evidence[circuit]
            ev["horses"]+=1
            runs=observed_runs(z["horse"],detail,limit=5)
            if any(num(x.get("marginSeconds")) is not None or num(x.get("timeBehindWinner")) is not None for x in runs):ev["A_marginObserved"]+=1
            if any(num(x.get("opponentLevel")) is not None for x in runs):ev["B_opponentObserved"]+=1
            if any(x.get("track")==detail.get("track") and x.get("surface") and x.get("surface")==detail.get("surface") and num(x.get("distance")) is not None and num(detail.get("distance")) is not None and abs(num(x.get("distance"))-num(detail.get("distance")))<=150 for x in runs):ev["C_courseObserved"]+=1
            if any(isinstance(x.get("cornerPositions"),list) and len(x.get("cornerPositions"))>=2 for x in runs):ev["D_cornerObserved"]+=1
            position = position_proxy(z["horse"], detail)
            if position is not None:
                variants.setdefault("mineta_position_proxy", {})[n] = position
            candidate = margin_abcde_score(z["horse"], detail)
            if candidate is not None:
                variants.setdefault("margin_abcde_352520155", {})[n] = candidate["score"]
            for key,value in candidates(z["horse"],detail).items():
                variants.setdefault(key,{})[n]=value
        field_scores=mineta_field_scores([z["horse"] for z in rows],detail)
        full=set(variants["current"])
        if set(field_scores)==full:
            variants["mineta_field_proxy"]=field_scores
            variants["mineta_current_60_40"]={n:.6*field_scores[n]+.4*variants["current"][n] for n in full}
            margin=variants.get("margin_abcde_352520155",{})
            if set(margin)==full:
                variants["mineta_margin_60_40"]={n:.6*field_scores[n]+.4*margin[n] for n in full}
                variants["mineta_current_margin_60_20_20"]={n:.6*field_scores[n]+.2*variants["current"][n]+.2*margin[n] for n in full}
        current_order = sorted(variants["current"], key=lambda n: (-variants["current"][n], n))
        abcde_scores = variants.get("margin_abcde_352520155", {})
        position_scores = variants.get("mineta_position_proxy", {})
        position_order = sorted(position_scores, key=lambda n: (-position_scores[n],n)) if set(position_scores)==set(variants["current"]) else []
        mixed_keys=("mineta_field_proxy","mineta_current_60_40","mineta_margin_60_40","mineta_current_margin_60_20_20")
        mixed_order={key:sorted(variants[key],key=lambda n:(-variants[key][n],n))
                     for key in mixed_keys if key in variants}
        raw_field_counts={k:0 for k in ("margin","marginSeconds","timeBehindWinner","time","opponentLevel")}
        for z in rows:
            for run in observed_runs(z["horse"],detail,limit=5):
                for k in raw_field_counts:
                    if run.get(k) not in (None,""): raw_field_counts[k]+=1
        if circuit in ("中央", "地方"):
            pilot.append({
                "date": str(detail.get("date") or ""),
                "raceId": str(detail.get("id") or ""),
                "circuit": circuit,
                "track": str(detail.get("track") or ""),
                "raceNumber": int(detail.get("raceNumber") or 0),
                "actualWinner": order[0],
                "currentTop": current_order[0],
                "currentWinnerRank": (current_order.index(order[0]) + 1
                                      if order[0] in current_order else None),
                "currentTop3Hit": order[0] in current_order[:3],
                "rankedHorses": len(current_order),
                "historicalInputFieldCounts":raw_field_counts,
                "fieldAwareObservedHorses":len(field_scores),
                "mixedForecasts":{key:{"topHorse":mixed_order[key][0],"winnerRank":mixed_order[key].index(order[0])+1 if order[0] in mixed_order[key] else None} if key in mixed_order else {"status":"missing-required-evidence"} for key in mixed_keys},
                "positionObservedHorses": len(position_scores),
                "positionComparable": bool(position_order),
                "positionTop": position_order[0] if position_order else None,
                "positionWinnerRank": (position_order.index(order[0])+1 if position_order and order[0] in position_order else None),
                "abcdeEligibleHorses": len(abcde_scores),
                "abcdeComparable": set(abcde_scores) == set(variants["current"]),
                "abcdeTop": (sorted(abcde_scores, key=lambda n: (-abcde_scores[n], n))[0]
                             if set(abcde_scores) == set(variants["current"]) else None),
            })
        if "reliability" not in variants or set(variants["reliability"]) != set(variants["current"]):
            coverage["common-set-missing"]+=1
            continue
        for name,values in variants.items():
            if set(values)!=set(variants["current"]) or order[0] not in values:
                coverage[name]+=1
                continue
            ranked=sorted(values,key=lambda n:(-values[n],n))
            mx=max(values.values())
            weights={n:math.exp(5*(v-mx)) for n,v in values.items()}
            p=weights[order[0]]/sum(weights.values())
            m=results[name]
            m["races"]+=1;m["top1"]+=int(ranked[0]==order[0])
            m["top3"]+=int(order[0] in ranked[:3])
            m["logLossSum"]+=-math.log(max(p,1e-15))
    jra=[r for r in pilot if r["circuit"]=="中央"]
    nar=[r for r in pilot if r["circuit"]=="地方"]
    five=(jra[:2]+nar[:3])
    if len(five)<5:
        used={r["raceId"] for r in five}
        five.extend(r for r in pilot if r["raceId"] not in used)
    chosen=five[:5]
    comparison,same_five=summarize_five(chosen)
    return {"version":"research-retrospective-v3","fiveRacePilot":chosen,
            "fiveRaceComparison":comparison,"sameFiveCoverage":same_five,
            "pilotSelection":"up to 2 JRA and 3 NAR from dated snapshots with observed winners","inputEnvelopes":envelopes,
            "matchedResultRaces":len(outcomes),
            "results":{k:{**v,"top1Rate":v["top1"]/v["races"],
                "top3Rate":v["top3"]/v["races"],
                "meanLogLoss":v["logLossSum"]/v["races"]}
                for k,v in results.items() if v["races"]},
            "evidenceCoverageByCircuit":{c:dict(v) for c,v in evidence.items()},
            "missingEvidenceByVariant":dict(coverage),
            "warning":"Retrospective snapshot inputs may contain post-race changes; not exact pre-off evidence. Different candidate coverage and fixed uncalibrated temperature. Not promotion proof."}

if __name__=="__main__":
    from sys import argv
    out=evaluate()
    Path(argv[1]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+chr(10))
    print("RESULT="+json.dumps(out,ensure_ascii=False))
