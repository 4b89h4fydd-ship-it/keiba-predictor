#!/usr/bin/env python3
"""Cycle: diagnose missing history gate; test original vs research gate (1 or 2
unknown-history horses) using SAME trained learner and scenario forecaster.
Read-only existing API, no race archival or new data route, JRA/NAR separated.
"""
import json
from collections import Counter
from datetime import date,timedelta
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family,race_evidence
from arvexq.prediction.new_forecast import build_forecast
ds=[(date(2026,10,15)+timedelta(days=i)).isoformat() for i in range(7)]
rows={}
for d in ds:rows[d]=day(d)
options={"original":0,"allow_one_unknown":1,"allow_two_unknown":2}
for circuit in ("地方","中央"):
 earlier=[];each=[]
 for d in ds:
  train=[r for r in earlier if r.get("circuit")==circuit]
  try:model=fit_model(train,circuit=circuit)
  except ValueError:
   earlier.extend(rows[d]);continue
  metrics={name:Counter() for name in options}
  issues=Counter()
  cases=[]
  for original in rows[d]:
   if original.get("circuit")!=circuit or race_family(original)!="flat" or (original.get("result") or {}).get("status")!="確定":continue
   places=finish_order(original)
   if not places:continue
   clean=scrub_for_replay(original,d)
   raw_reports=race_evidence(clean)
   unknown=[r["horseNumber"] for r in raw_reports if not r["observedStarts"]]
   issues["finished_races"]+=1
   issues["unknown_"+str(len(unknown))]+=1
   if places[0] in unknown:issues["actual_winner_unknown_history"]+=1
   predicted={}
   for name,limit in options.items():
    try:
     pred=build_forecast(clean,model,research_max_unknown_history=limit)
    except (ValueError,TypeError,KeyError,OverflowError):
     metrics[name]["error"]+=1;continue
    if pred.get("predictionStatus")!="candidate-analysis":
     metrics[name]["no_mark"]+=1;continue
    marks=[int(h["horseNumber"]) for h in pred["horses"] if (h.get("integratedEvaluation") or {}).get("mark")=="◎"]
    if len(marks)!=1:metrics[name]["no_mark"]+=1;continue
    horse=marks[0];predicted[name]=horse
    metrics[name]["scored"]+=1
    metrics[name]["hits"]+=int(horse==places[0])
    metrics[name]["top3"]+=int(horse in places[:3])
    metrics[name]["picked_missing_history"]+=int(horse in unknown)
   for name in ("allow_one_unknown","allow_two_unknown"):
    if name in predicted and "original" not in predicted:
     issues[name+"_rescued"]+=1
     issues[name+"_rescued_hits"]+=int(predicted[name]==places[0])
     if len(cases)<10:cases.append({"race":original["id"],"unknown_history_horses":unknown,"winner":places[0],"research_pick":predicted[name],"case":name})
    elif name in predicted and "original" in predicted and predicted[name]!=predicted["original"]:
     issues[name+"_changed_existing"]+=1
     issues[name+"_changed_win_gain"]+=int(predicted[name]==places[0])-int(predicted["original"]==places[0])
  item={"day":d,"phase":"holdout" if d>="2026-10-20" else "validation","trained_races":model["training"]["races"],
        "outcomes":{name:dict(v) for name,v in metrics.items()},"causes":dict(issues),"examples":cases}
  each.append(item)
  print("MISSING_HISTORY_DAY",json.dumps({"circuit":circuit,**item},ensure_ascii=False),flush=True)
  earlier.extend(rows[d])
 def totals(phase,name):
  c=Counter()
  for r in each:
   if r["phase"]==phase:c.update(r["outcomes"][name])
  return {key:c[key] for key in ("scored","hits","top3","no_mark","error","picked_missing_history")}
 base=totals("validation","original")
 better=[name for name in ("allow_one_unknown","allow_two_unknown") if totals("validation",name)["hits"]>base["hits"] and totals("validation",name)["error"]==base["error"]]
 chosen=sorted(better,key=lambda n:(-totals("validation",n)["hits"],n))[0] if better else None
 val=[r for r in each if r["phase"]=="validation"];hold=[r for r in each if r["phase"]=="holdout"]
 hbase=totals("holdout","original");hcand=totals("holdout",chosen) if chosen else None
 improved=bool(chosen and hold and hcand["hits"]>hbase["hits"] and hcand["error"]==hbase["error"])
 causes=Counter()
 for r in each:causes.update(r["causes"])
 print("MISSING_HISTORY_FINAL",json.dumps({"circuit":circuit,"validation_days":[r["day"] for r in val],"holdout_days":[r["day"] for r in hold],
  "outcomes":{n:{"validation":totals("validation",n),"holdout":totals("holdout",n)} for n in options},
  "missing_histogram":{k:v for k,v in causes.items() if k.startswith("unknown_")},
  "actual_winner_unknown_history":causes["actual_winner_unknown_history"],"selected_on_validation":chosen,
  "holdout_improvement":improved,"decision":"research_only_further_proof_needed" if improved else "no_confirmed_improvement",
  "data_integrity":"Retrospective as-of feature timestamps not verified; no production adoption."},ensure_ascii=False),flush=True)
