#!/usr/bin/env python3
"""Research full cycle: original fit_model vs winner-focused gradient 2x and 4x.
Uses same learned_scenarios & new_forecast, different training loss emphasis only.
Chronological expanding window, separate JRA/NAR, dates 2026-10-15..21.
"""
from collections import Counter
from datetime import date,timedelta
import json
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family
from arvexq.prediction.new_forecast import build_forecast
START=date(2026,10,15);END=date(2026,10,21)
HOLDOUT="2026-10-20"
VARIANTS={"original":1.0,"winner2x":2.0,"winner4x":4.0}
dates=[(START+timedelta(days=i)).isoformat() for i in range((END-START).days+1)]
data={}
fails={}
for ds in dates:
 try:data[ds]=day(ds)
 except Exception as e:fails[ds]=type(e).__name__
if fails:raise SystemExit("Failed to obtain all days: "+json.dumps(fails))

def evaluate(circuit,ds,rows,models):
 metrics={name:Counter() for name in VARIANTS}
 changes=Counter()
 for d in rows:
  if d.get("circuit")!=circuit or race_family(d)!="flat" or (d.get("result") or {}).get("status")!="確定":continue
  actual=finish_order(d)
  if not actual:continue
  clean=scrub_for_replay(d,ds)
  predictions={}
  for name,m in models.items():
   try:
    p=build_forecast(clean,m)
    if p.get("predictionStatus")!="candidate-analysis":
     metrics[name]["no_mark"]+=1;continue
    honmei=[int(h["horseNumber"]) for h in p["horses"] if (h.get("integratedEvaluation") or {}).get("mark")=="◎"]
    if len(honmei)!=1:metrics[name]["no_mark"]+=1;continue
    predictions[name]=honmei[0]
   except (ValueError,TypeError,KeyError,OverflowError):
    metrics[name]["error"]+=1
  # Every horse pick is produced before reading the realized first finisher.
  winning=actual[0]
  for name,pick in predictions.items():
   metrics[name]["scored"]+=1
   metrics[name]["hit"]+=int(pick==winning)
   metrics[name]["top3"]+=int(pick in actual[:3])
  if "original" in predictions:
   for name in VARIANTS:
    if name=="original" or name not in predictions:continue
    if predictions[name]!=predictions["original"]:
     changes[name+"_changed"]+=1
     changes[name+"_fixed"]+=int(predictions[name]==winning)
     changes[name+"_regressed"]+=int(predictions["original"]==winning)
 return metrics,dict(changes)

for circuit in ("地方","中央"):
 hist=[];reports=[]
 for ds in dates:
  old=[d for d in hist if d.get("circuit")==circuit]
  try:
   models={name:fit_model(old,circuit=circuit,winner_pair_weight=weight) for name,weight in VARIANTS.items()}
  except ValueError as e:
   print("WINNER_LOSS_NO_MODEL",json.dumps({"circuit":circuit,"day":ds,"reason":str(e)},ensure_ascii=False),flush=True)
   hist.extend(data[ds]);continue
  metric,changes=evaluate(circuit,ds,data[ds],models)
  if metric["original"]["scored"]:
   item={"day":ds,"phase":"holdout" if ds>=HOLDOUT else "validation","train_races":models["original"]["training"]["races"],
    "models":{n:dict(v) for n,v in metric.items()},"changes":changes}
   reports.append(item)
   print("WINNER_LOSS_DAY",json.dumps({"circuit":circuit,**item},ensure_ascii=False),flush=True)
  hist.extend(data[ds])
 def sum_phase(phase,name):
  c=Counter()
  for r in reports:
   if r["phase"]==phase:c.update(r["models"][name])
  return {k:c[k] for k in ("scored","hit","top3","no_mark","error")}
 base=sum_phase("validation","original")
 options=[name for name in VARIANTS if name!="original" and sum_phase("validation",name)["hit"]>base["hit"]
  and sum_phase("validation",name)["scored"]==base["scored"] and sum_phase("validation",name)["error"]==base["error"]]
 selected=sorted(options,key=lambda n:(-sum_phase("validation",n)["hit"],n))[0] if options else None
 valid_days=[r["day"] for r in reports if r["phase"]=="validation"]
 hold_days=[r["day"] for r in reports if r["phase"]=="holdout"]
 base_hold=sum_phase("holdout","original")
 cand_hold=sum_phase("holdout",selected) if selected else None
 confirmed=bool(selected and base_hold["scored"] and cand_hold["scored"]==base_hold["scored"] and cand_hold["hit"]>base_hold["hit"] and cand_hold["error"]==base_hold["error"])
 print("WINNER_LOSS_FINAL",json.dumps({"circuit":circuit,"validation_days":valid_days,"holdout_days":hold_days,
  "outcomes":{name:{"validation":sum_phase("validation",name),"holdout":sum_phase("holdout",name)} for name in VARIANTS},
  "selected_on_validation":selected,"improved_on_holdout":confirmed,
  "action":"research_candidate_only" if confirmed else "continue_next_cycle",
  "asof_feature_integrity_verified":False},ensure_ascii=False),flush=True)
