#!/usr/bin/env python3
"""Research-only existing three-scenario aggregate for honmei. Existing forecast
training stays unchanged: compare lower-bound vs mean, median, mean minus spread.
Sequential previous-date fit, independent holdout. NO production changes.
"""
from collections import Counter
from datetime import date,timedelta
from statistics import median
import json
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family
from arvexq.prediction.new_forecast import build_forecast
variants=("original","mean_win","median_win","mean_minus_spread")
dates=[(date(2026,10,15)+timedelta(days=i)).isoformat() for i in range(7)]
all_data={d:day(d) for d in dates}
def winner(analysis,mode):
 scenarios=analysis["scenarios"]
 if not scenarios:return None
 ranks={}
 for r in analysis["reports"]:
  number=r["horseNumber"]
  probs=[s["probabilities"][number]["win"] for s in scenarios]
  if mode=="original":score=min(probs)
  elif mode=="mean_win":score=sum(probs)/len(probs)
  elif mode=="median_win":score=median(probs)
  else:score=sum(probs)/len(probs)-0.5*(max(probs)-min(probs))
  ranks[number]=(score,min(s["probabilities"][number]["top3"] for s in scenarios))
 return min(ranks,key=lambda n:(-ranks[n][0],-ranks[n][1],n))
for circuit in ("地方","中央"):
 history=[];reports=[]
 for ds in dates:
  prev=[r for r in history if r.get("circuit")==circuit]
  try:model=fit_model(prev,circuit=circuit)
  except ValueError:
   history.extend(all_data[ds]);continue
  counts={v:Counter() for v in variants}
  differences=Counter()
  for r in all_data[ds]:
   if r.get("circuit")!=circuit or race_family(r)!="flat" or (r.get("result") or {}).get("status")!="確定":continue
   order=finish_order(r)
   if not order:continue
   try:pred=build_forecast(scrub_for_replay(r,ds),model)
   except (ValueError,TypeError,KeyError,OverflowError):
    for v in variants:counts[v]["errors"]+=1
    continue
   if pred.get("predictionStatus")!="candidate-analysis":
    for v in variants:counts[v]["no_mark"]+=1
    continue
   picks={v:winner(pred["scenarioAnalysis"],v) for v in variants}
   for v,n in picks.items():
    if n is None:counts[v]["no_mark"]+=1;continue
    counts[v]["scored"]+=1;counts[v]["hits"]+=int(n==order[0]);counts[v]["top3"]+=int(n in order[:3])
   for v in variants[1:]:
    if picks[v]!=picks["original"]:
     differences[v+"_changed"]+=1
     differences[v+"_fixed"]+=int(picks[v]==order[0])
     differences[v+"_lost"]+=int(picks["original"]==order[0])
  if counts["original"]["scored"]:
   record={"day":ds,"phase":"holdout" if ds>="2026-10-20" else "validation","train_races":model["training"]["races"],
           "models":{k:dict(v) for k,v in counts.items()},"differences":dict(differences)}
   reports.append(record)
   print("SCENARIO_AGGREGATION_DAY",json.dumps({"circuit":circuit,**record},ensure_ascii=False),flush=True)
  history.extend(all_data[ds])
 def total(phase,v):
  x=Counter()
  for r in reports:
   if r["phase"]==phase:x.update(r["models"][v])
  return {key:x[key] for key in ("scored","hits","top3","no_mark","errors")}
 base=total("validation","original")
 eligible=[v for v in variants[1:] if total("validation",v)["hits"]>base["hits"] and total("validation",v)["scored"]==base["scored"] and total("validation",v)["errors"]==base["errors"]]
 chosen=sorted(eligible,key=lambda k:(-total("validation",k)["hits"],k))[0] if eligible else None
 h=total("holdout","original");c=total("holdout",chosen) if chosen else {}
 confirmed=bool(chosen and h["scored"] and c["scored"]==h["scored"] and c["hits"]>h["hits"] and c["errors"]==h["errors"])
 print("SCENARIO_AGGREGATION_FINAL",json.dumps({"circuit":circuit,"validation_days":[r["day"] for r in reports if r["phase"]=="validation"],
 "holdout_days":[r["day"] for r in reports if r["phase"]=="holdout"],"outcomes":{v:{"validation":total("validation",v),"holdout":total("holdout",v)} for v in variants},
 "selected_validation_only":chosen,"holdout_improved":confirmed,"decision":"research_candidate_only" if confirmed else "no_confirmed_improvement",
 "asof_inputs_verified":False},ensure_ascii=False),flush=True)
