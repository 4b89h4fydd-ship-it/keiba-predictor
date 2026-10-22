#!/usr/bin/env python3
"""Same existing learned_scenarios+new_forecast, baseline and tuned existing l2.
15 Oct train -> 16 Oct diagnose/select -> 17 Oct unseen holdout.
No persistent race store and no production algorithm changes.
"""
from __future__ import annotations
import json,os
from collections import Counter
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family
from arvexq.prediction.new_forecast import build_forecast

# The pilot's imported original two-day experiment also executes (auditable).
train=day("2026-10-15")
validation=day("2026-10-16")
holdout=day("2026-10-17")
def evaluate(races,model,label):
 res=Counter(); misses=[]
 for original in races:
  if original.get("circuit")!="地方" or (original.get("result") or {}).get("status")!="確定":continue
  if race_family(original)!="flat":
   res["not_flat_family"]+=1;continue
  order=finish_order(original)
  if not order:continue
  candidate=scrub_for_replay(original,original["date"])
  try:
   pred=build_forecast(candidate,model)
  except (ValueError,TypeError,KeyError,OverflowError):
   res["model_exception"]+=1;continue
  if pred.get("predictionStatus")!="candidate-analysis":
   res["no_mark"]+=1;continue
  marks={int(h["horseNumber"]):(h.get("integratedEvaluation") or {}).get("mark","") for h in pred.get("horses") or [] if h.get("horseNumber")}
  pick=next((n for n,m in marks.items() if m=="◎"),None)
  if pick is None:
   res["no_honmei"]+=1;continue
  res["scored"]+=1;res["hits"]+=int(pick==order[0])
  if pick!=order[0]:
   reports=(pred.get("scenarioAnalysis") or {}).get("reports") or []
   by={r["horseNumber"]:r for r in reports}
   chosen=by.get(pick,{}).get("featureValues") or {}
   winner=by.get(order[0],{}).get("featureValues") or {}
   keys=("win_rate","recent_finish_mean","same_distance_finish","same_track_finish","early_position","closing_gain")
   misses.append({"raceId":original["id"],"predicted":pick,"winner":order[0],
                  "marks":marks,"features":{k:{"predicted":chosen.get(k),"winner":winner.get(k)} for k in keys}})
 print("SAME_MODEL_EXPERIMENT",json.dumps({"model":label,"train_end":model["training"]["lastDate"],"day":races[0]["date"] if races else None,
    "races":dict(res),"win_rate":round(res["hits"]/res["scored"],4) if res["scored"] else None,"misses":len(misses),"miss_examples":misses[:3]},ensure_ascii=False),flush=True)
 return res
models={}
for label,l2 in (("existing_l2_001",0.01),("candidate_l2_003",0.03)):
 models[label]=fit_model(train,circuit="地方",l2=l2)
validation_scores={name:evaluate(validation,model,name) for name,model in models.items()}
# Tune against the earlier validation date only. Unseen holdout is not used to choose.
choices=sorted(validation_scores,key=lambda name:(-validation_scores[name]["hits"]/max(1,validation_scores[name]["scored"]),0 if name=="existing_l2_001" else 1))
chosen=choices[0]
print("MODEL_SELECTION_ON_VALIDATION_ONLY",json.dumps({"selected":chosen,"scores":{k:dict(v) for k,v in validation_scores.items()}},ensure_ascii=False),flush=True)
baseline=fit_model(train+validation,circuit="地方",l2=0.01)
modified=fit_model(train+validation,circuit="地方",l2=0.03)
b=evaluate(holdout,baseline,"holdout_existing_l2_001")
m=evaluate(holdout,modified,"holdout_candidate_l2_003")
print("UNSEEN_HOLDOUT_COMPARISON",json.dumps({"holdout_date":"2026-10-17","selection":chosen,"baseline":dict(b),"candidate":dict(m),
 "better":m["hits"]>b["hits"] if b["scored"]==m["scored"] else None,
 "promotion_recommended":bool(chosen=="candidate_l2_003" and m["scored"]==b["scored"] and m["hits"]>b["hits"]),"selected_from_validation":chosen},ensure_ascii=False),flush=True)
if not b["scored"] or not m["scored"]:raise SystemExit("No real-race holdout scoring; invalid experiment")
