#!/usr/bin/env python3
"""Research-only one-cycle test of a revised honmei selection INSIDE the existing
learned-scenarios forecaster, not a new standalone predictor.

Idea from miss diagnostics: raw win track record may be underestimated versus
recent-form/track fit. Blend existing scenario win lower-bound and shrinkage-
adjusted observed win rate. Walk-forward dates, separate circuits, untouched
holdout. No save, no production or main changes. Snapshot as-of inputs NOT proven.
"""
from collections import Counter,defaultdict
from datetime import date,timedelta
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family
from arvexq.prediction.new_forecast import build_forecast

START=date(2026,10,15);END=date(2026,10,21)
CANDIDATES={"blend15":0.15,"blend30":0.30,"blend50":0.50}
PHASE_BOUNDARY=date(2026,10,20).isoformat()

def choose(analysis,blend):
 reports=analysis["reports"];scenarios=analysis["scenarios"]
 if not scenarios:return None
 n=len(reports)
 if not n:return None
 # Existing winner lower bound used by original _decide.
 base={r["horseNumber"]:min(s["probabilities"][r["horseNumber"]]["win"] for s in scenarios) for r in reports}
 if blend==0:return min(base,key=lambda h:(-base[h],-min(s["probabilities"][h]["top3"] for s in scenarios),h))
 prior={}
 for r in reports:
  nstarts=int(r["observedStarts"] or 0)
  rate=r["featureValues"].get("win_rate")
  wins=(float(rate)*nstarts) if rate is not None and nstarts else 0.
  # Conservative prior with 8 equivalent starts at equal-field likelihood.
  prior[r["horseNumber"]]=(wins+8.0/n)/(nstarts+8.0)
 total=sum(prior.values())
 scores={h:(1-blend)*base[h]+blend*prior[h]/total for h in base}
 return min(scores,key=lambda h:(-scores[h],-base[h],h))

dates=[(START+timedelta(days=i)).isoformat() for i in range((END-START).days+1)]
data={}
errors={}
for ds in dates:
 try:data[ds]=day(ds)
 except Exception as exc:
  errors[ds]=type(exc).__name__
  print("BAYES_CYCLE_DAY_ERROR",ds,type(exc).__name__,flush=True)
if errors:raise SystemExit("Date coverage incomplete: "+str(errors))
for circuit in ("地方","中央"):
 history=[];evaluations=[]
 for ds in dates:
  batch=data[ds];older=[r for r in history if r.get("circuit")==circuit]
  try:model=fit_model(older,circuit=circuit)
  except ValueError:
   history.extend(batch);continue
  metric={name:Counter() for name in ["original",*CANDIDATES]}
  changes=Counter()
  for original in batch:
   if original.get("circuit")!=circuit or race_family(original)!="flat" or (original.get("result") or {}).get("status")!="確定":continue
   actual=finish_order(original)
   if not actual:continue
   pre=scrub_for_replay(original,ds)
   try:
    pred=build_forecast(pre,model)
   except (ValueError,KeyError,TypeError,OverflowError):
    for v in metric.values():v["errors"]+=1
    continue
   if pred.get("predictionStatus")!="candidate-analysis":
    for v in metric.values():v["unscorable"]+=1
    continue
   analysis=pred["scenarioAnalysis"]
   picks={"original":choose(analysis,0.0)}
   for name,blend in CANDIDATES.items():picks[name]=choose(analysis,blend)
   # All model predictions and candidates are fixed before looking up winner.
   winner=actual[0]
   for name,pick in picks.items():
    if pick is None:metric[name]["unscorable"]+=1;continue
    metric[name]["scored"]+=1
    metric[name]["hits"]+=int(pick==winner)
    metric[name]["top3"]+=int(pick in actual[:3])
   for name in CANDIDATES:
    if picks[name]!=picks["original"]:
     changes[name+"_changed"]+=1
     changes[name+"_fixed"]+=int(picks[name]==winner)
     changes[name+"_lost"]+=int(picks["original"]==winner)
  if metric["original"]["scored"]:
   result={"date":ds,"phase":"holdout" if ds>=PHASE_BOUNDARY else "validation",
    "trained_races":model["training"]["races"],"models":{k:dict(v) for k,v in metric.items()},"changes":dict(changes)}
   evaluations.append(result)
   print("BAYES_CYCLE_DAY",__import__("json").dumps({"circuit":circuit,**result},ensure_ascii=False),flush=True)
  history.extend(batch)
 def total(phase,name):
  c=Counter()
  for r in evaluations:
   if r["phase"]==phase:c.update(r["models"][name])
  return {k:c[k] for k in ("scored","hits","top3","errors","unscorable")}
 val=total("validation","original");hold=total("holdout","original")
 chosen=None
 options=[k for k in CANDIDATES if total("validation",k)["scored"]==val["scored"] and total("validation",k)["hits"]>val["hits"]]
 if options:chosen=sorted(options,key=lambda k:(-total("validation",k)["hits"],k))[0]
 confirmed=bool(chosen and hold["scored"] and total("holdout",chosen)["scored"]==hold["scored"] and total("holdout",chosen)["hits"]>hold["hits"])
 print("BAYES_CYCLE_FINAL",__import__("json").dumps({"circuit":circuit,
  "validation_days":[r["date"] for r in evaluations if r["phase"]=="validation"],
  "holdout_days":[r["date"] for r in evaluations if r["phase"]=="holdout"],
  "original":{"validation":val,"holdout":hold},
  "candidates":{k:{"validation":total("validation",k),"holdout":total("holdout",k)} for k in CANDIDATES},
  "candidate_selected_using_validation_only":chosen,"improvement_confirmed":confirmed,
  "action":"research_only_not_production" if confirmed else "not_accepted_continue_research",
  "preoff_asof_verified":False},ensure_ascii=False),flush=True)
