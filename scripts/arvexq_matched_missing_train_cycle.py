#!/usr/bin/env python3
"""Research: control strict original vs relaxed prediction-only vs matched training
and prediction missing-history policy. Same learned pairwise model and features.
Chronological 7 day source, 6 scoring days, independent holdout, separate circuits.
"""
import json
from collections import Counter
from datetime import date,timedelta
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family,race_evidence
from arvexq.prediction.new_forecast import build_forecast
dates=[(date(2026,10,15)+timedelta(days=i)).isoformat() for i in range(7)]
all_days={d:day(d) for d in dates}
configs={"strict_original":("strict",0),"prediction_only_one":("strict",1),"matched_train_predict_one":("matched",1)}
for circuit in ("地方","中央"):
 hist=[];report=[];issue_total=Counter()
 for ds in dates:
  history=[r for r in hist if r.get("circuit")==circuit]
  try:original=fit_model(history,circuit=circuit)
  except ValueError:
   hist.extend(all_days[ds]);continue
  try:matched=fit_model(history,circuit=circuit,research_max_unknown_history=1)
  except ValueError:matched=None
  models={"strict":original,"matched":matched}
  counts={v:Counter() for v in configs}
  diffs=Counter()
  for target in all_days[ds]:
   if target.get("circuit")!=circuit or race_family(target)!="flat" or (target.get("result") or {}).get("status")!="確定":continue
   finishes=finish_order(target)
   if not finishes:continue
   clean=scrub_for_replay(target,ds)
   unknown=sum(not r["observedStarts"] for r in race_evidence(clean))
   issue_total["unknown_"+str(unknown)]+=1
   picks={}
   for config,(kind,allowance) in configs.items():
    model=models[kind]
    if model is None:counts[config]["no_model"]+=1;continue
    try:
     pred=build_forecast(clean,model,research_max_unknown_history=allowance)
     if pred.get("predictionStatus")!="candidate-analysis":
      counts[config]["no_mark"]+=1;continue
     honmei=[int(h["horseNumber"]) for h in pred["horses"] if (h.get("integratedEvaluation") or {}).get("mark")=="◎"]
     if len(honmei)!=1:counts[config]["no_mark"]+=1;continue
     picks[config]=honmei[0]
    except (ValueError,TypeError,KeyError,OverflowError):
     counts[config]["errors"]+=1
   # Forecasts for all configs fixed prior to examining winner label.
   winner=finishes[0]
   for config,pick in picks.items():
    counts[config]["scored"]+=1
    counts[config]["hits"]+=int(pick==winner)
    counts[config]["top3"]+=int(pick in finishes[:3])
   for name in configs:
    if name=="strict_original" or name not in picks:continue
    if name in picks and "strict_original" not in picks:
     diffs[name+"_rescued"]+=1
     diffs[name+"_rescued_win"]+=int(picks[name]==winner)
    elif picks[name]!=picks["strict_original"]:
     diffs[name+"_changed"]+=1
     diffs[name+"_gain"]+=int(picks[name]==winner)-int(picks["strict_original"]==winner)
  if counts["strict_original"]["scored"]:
   row={"day":ds,"phase":"holdout" if ds>="2026-10-20" else "validation",
    "original_training":original["training"]["races"],
    "matched_training":matched["training"]["races"] if matched else 0,
    "outcomes":{v:dict(c) for v,c in counts.items()},"changes":dict(diffs)}
   report.append(row)
   print("MATCHED_MISSING_DAY",json.dumps({"circuit":circuit,**row},ensure_ascii=False),flush=True)
  hist.extend(all_days[ds])
 def summ(phase,name):
  c=Counter()
  for r in report:
   if r["phase"]==phase:c.update(r["outcomes"][name])
  return {k:c[k] for k in ("scored","hits","top3","no_mark","errors","no_model")}
 base=summ("validation","strict_original")
 choices=[n for n in configs if n!="strict_original" and summ("validation",n)["scored"] and base["scored"]
          and summ("validation",n)["hits"]*base["scored"]>base["hits"]*summ("validation",n)["scored"]
          and summ("validation",n)["errors"]==base["errors"]]
 chosen=sorted(choices,key=lambda n:(-summ("validation",n)["hits"]/summ("validation",n)["scored"],n))[0] if choices else None
 hbase=summ("holdout","strict_original");hcan=summ("holdout",chosen) if chosen else None
 success=bool(chosen and hbase["scored"] and hcan["scored"] and hcan["hits"]*hbase["scored"]>hbase["hits"]*hcan["scored"] and hcan["errors"]==hbase["errors"])
 print("MATCHED_MISSING_FINAL",json.dumps({"circuit":circuit,"validation_days":[r["day"] for r in report if r["phase"]=="validation"],
  "holdout_days":[r["day"] for r in report if r["phase"]=="holdout"],
  "outcomes":{n:{"validation":summ("validation",n),"holdout":summ("holdout",n)} for n in configs},
  "selected_from_validation":chosen,"holdout_hit_rate_improved":success,
  "decision":"research_candidate_only" if success else "do_not_adopt","missing_histogram":dict(issue_total),
  "asof_input_integrity_verified":False},ensure_ascii=False),flush=True)
