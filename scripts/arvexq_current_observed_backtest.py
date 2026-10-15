#!/usr/bin/env python3
"""Read-only historical replay of the CURRENT 60/40 scorer, with explicit missing-input audit."""
from __future__ import annotations
import argparse
import copy
import json
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from arvexq.prediction.observed_model import apply_observed_marks, model_version

def fetch_json(url):
    request=urllib.request.Request(url,headers={"User-Agent":"ARVEXQ-research-observed-6040/1.0"})
    with urllib.request.urlopen(request,timeout=25) as response:
        return json.load(response)

def evaluate(details):
    counts=Counter()
    circuits={}
    rows=[]
    for raw in details:
        if not isinstance(raw,dict):
            continue
        counts["examined"]+=1
        circuit=str(raw.get("circuit") or "")
        if circuit not in ("地方","中央","NAR","JRA","local","central"):
            counts["unknown_circuit"]+=1; continue
        horses=raw.get("horses") or []
        result=(raw.get("result") or {}).get("finishers") or []
        finish={}
        for x in result:
            try:
                pos=int(x.get("finish") or 0);number=int(x.get("horseNumber") or 0)
                if pos>0 and number>0:finish[number]=pos
            except (ValueError,TypeError):pass
        if not finish or not horses:
            counts["missing_result_or_entries"]+=1;continue
        observed=sum(bool(h.get("recentRaces") or h.get("allPastRuns") or h.get("careerArchive")) for h in horses)
        if observed<len(horses):
            counts["missing_history"]+=1
        pre=copy.deepcopy(raw)
        pre.pop("result",None)
        pre.pop("payouts",None)
        pre.pop("raceStatus",None)
        pre.pop("finishers",None)
        for h in pre.get("horses") or []:
            for k in ("finish","finishPosition","resultTime","winOdds","popularity","marketProbability","payout"):
                h.pop(k,None)
            h.pop("integratedEvaluation",None)
        apply_observed_marks(pre)
        ranking=pre.get("factorRanking") or []
        if pre.get("predictionStatus")!="ready" or not ranking:
            counts["incomplete_current_6040"]+=1
            rows.append({"id":raw.get("id"),"circuit":circuit,"status":"unscorable",
                         "coverage":pre.get("observedModelCoverage"),"modelVersion":model_version(pre)})
            continue
        winner=next((number for number,pos in finish.items() if pos==1),None)
        if winner is None:
            counts["missing_winner"]+=1;continue
        picks=[x["horseNumber"] for x in ranking]
        target=circuits.setdefault(circuit,Counter())
        counts["scored"]+=1;target["scored"]+=1
        if picks[0]==winner:counts["top1"]+=1;target["top1"]+=1
        if winner in picks[:3]:counts["top3"]+=1;target["top3"]+=1
        if set(finishers for finishers,pos in finish.items() if pos<=3).issubset(set(picks[:6])):
            counts["podium_in_top6"]+=1;target["podium_in_top6"]+=1
        rows.append({"id":raw.get("id"),"circuit":circuit,"status":"scored",
                     "modelVersion":model_version(pre),"winner":winner,
                     "top1":picks[0],"top3":picks[:3],"top1Hit":picks[0]==winner,
                     "winnerTop3":winner in picks[:3]})
    return {"counts":dict(counts),"byCircuit":{k:dict(v) for k,v in circuits.items()},"races":rows,
            "policy":"No results or current odds in model inputs; no retrospective score substitution."}

def collect(api,days,stop):
    races=[];errors=[];today=date.today()
    for offset in range(1,days+1):
        d=today-timedelta(days=offset)
        url=api.rstrip("/")+"/api/day?"+urlencode({"date":d.isoformat(),"details":"1"})
        try:
            payload=fetch_json(url)
            races.extend(payload.get("details") or [])
        except Exception as exc:
            errors.append({"date":d.isoformat(),"error":str(exc)[:240]})
        if stop and len(races)>=stop:break
    return races,errors

def enrich_historical_jra(details, maximum):
    """Attempt independent historical entry/official past-margin collection.
    The label is removed BEFORE any historical information is requested."""
    import app as prod
    tried=0;found=0;errors=[]
    for d in details:
        if tried>=maximum:break
        if str(d.get("circuit") or "") not in ("中央","JRA","central"):continue
        if not (d.get("result") or {}).get("finishers"):continue
        tried+=1
        label=d.get("result")
        pre=copy.deepcopy(d)
        pre.pop("result",None)
        for h in pre.get("horses") or []:
            for k in ("finishPosition","currentFinish","resultTime","winOdds","popularity","marketProbability"):
                h.pop(k,None)
        try:
            # Production historical parser already handles IDs / card formats.
            parsed=prod._netkeiba_detail_rows(pre) or []
            if not parsed:raise ValueError("historical-entry-card-empty")
            pre["horses"]=parsed
            pre=prod._strip_excluded(prod._apply_enrichment(str(d.get("id") or ""),pre))
            pre=prod._attach_stored_career(pre)
            if any(h.get("recentRaces") or h.get("allPastRuns") for h in pre.get("horses") or []):
                d["horses"]=pre["horses"]
                found+=1
        except Exception as exc:
            errors.append({"id":d.get("id"),"error":str(exc)[:190]})
        d["result"]=label
    return {"attempted":tried,"withHistory":found,"errors":errors,
            "example": [{"id": d.get("id"),"track":d.get("track"),"horseEvidence":[{"horseNumber":h.get("horseNumber"),"runs":len(h.get("recentRaces") or h.get("allPastRuns") or []),"keys":list((h.get("recentRaces") or h.get("allPastRuns") or [{}])[0].keys())[:25]} for h in (d.get("horses") or [])[:3]]} for d in details if str(d.get("circuit") or "") in ("中央","JRA","central")][:3]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--api",default="https://kraiz-api.4b89h4fydd.workers.dev")
    p.add_argument("--days",type=int,default=21)
    p.add_argument("--max-races",type=int,default=500)
    p.add_argument("--input",action="append",default=[])
    p.add_argument("--enrich-jra",type=int,default=0)
    p.add_argument("--out",default="research-output/current-observed-6040")
    args=p.parse_args()
    details=[];errors=[]
    if args.input:
        for filename in args.input:
            payload=json.loads(Path(filename).read_text(encoding="utf-8"))
            details.extend(payload.get("details") or [])
    else:details,errors=collect(args.api,args.days,args.max_races)
    enrichment=enrich_historical_jra(details,args.enrich_jra) if args.enrich_jra else None
    report=evaluate(details)
    if enrichment is not None:report["jraHistoricalEnrichment"]=enrichment
    report["fetchErrors"]=errors
    report["fetchedRaceCount"]=len(details)
    report["currentMethod"]="arvexq observed 60% positioning + 40% margin, not archived forecast"
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="races"},ensure_ascii=False,indent=2))
    if not report["counts"].get("scored"):
        print("NO ELIGIBLE FULL-INPUT HISTORICAL RACES: cannot claim measured accuracy")
        return 2
    return 0

if __name__=="__main__":raise SystemExit(main())
