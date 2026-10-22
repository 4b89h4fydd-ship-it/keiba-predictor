#!/usr/bin/env python3
"""Existing ARVEXQ learner: explain each wrong honmei via observed input evidence
and existing model feature contributions; not a new algorithm or model revision.

Past reconstructed inputs are retrospective and may still contain late-mutated fields.
Do not label these scores genuine historical pre-off accuracy.
"""
import collections,json
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,FEATURES,_vector,race_family
from arvexq.prediction.new_forecast import build_forecast

d15=day("2026-10-15")
d16=day("2026-10-16")
d17=day("2026-10-17")
train=[(d15,d16),(d15+d16,d17)]
tot=collections.Counter()
win_adv=collections.Counter()
top_model_errors=collections.Counter()
missing_by_day=collections.Counter()
miss_cases=[]
for earlier,day_races in train:
 model=fit_model(earlier,circuit="地方")
 weights=model["weights"];n_features=len(FEATURES)
 for original in day_races:
  if original.get("circuit")!="地方" or race_family(original)!="flat" or (original.get("result") or {}).get("status")!="確定":continue
  order=finish_order(original)
  if not order:continue
  forecast=build_forecast(scrub_for_replay(original,original["date"]),model)
  if forecast.get("predictionStatus")!="candidate-analysis":
   tot["no_marks"]+=1;missing_by_day[original["date"]]+=1;continue
  marks={int(h["horseNumber"]):(h.get("integratedEvaluation") or {}).get("mark") for h in forecast.get("horses") or [] if h.get("horseNumber")}
  pick=next((no for no,mark in marks.items() if mark=="◎"),None)
  if not pick:tot["no_honmei"]+=1;continue
  winner=order[0];tot["scored"]+=1
  if pick==winner:tot["hits"]+=1;continue
  tot["misses"]+=1
  analysis=forecast["scenarioAnalysis"]
  reports={r["horseNumber"]:r for r in analysis["reports"]}
  if winner not in reports or pick not in reports:tot["missing_reports"]+=1;continue
  selected=reports[pick];actual=reports[winner]
  # Explicitly compare both original feature values and existing fitted coefficients.
  xp=_vector(selected,model["centers"],model["scales"])
  xw=_vector(actual,model["centers"],model["scales"])
  contributions=[]
  missing=[]
  for i,key in enumerate(FEATURES):
   a=selected["featureValues"].get(key)
   b=actual["featureValues"].get(key)
   if a is None or b is None:
    missing.append(key)
    continue
   if b>a:win_adv[key]+=1
   impact=(xp[i]-xw[i])*weights[i]+(xp[i+n_features]-xw[i+n_features])*weights[i+n_features]
   contributions.append((key,round(impact,5),round(float(a),5),round(float(b),5)))
  contributions.sort(key=lambda t:-t[1])
  for key,impact,*_ in contributions[:3]:
   if impact>0:top_model_errors[key]+=1
  scenarios=[]
  for scene in analysis["scenarios"]:
   ps=scene.get("probabilities") or {}
   if pick in ps and winner in ps:
    scenarios.append({"scenario":scene["id"],"pick_win":round(ps[pick]["win"],4),"winner_win":round(ps[winner]["win"],4)})
  row={"date":original["date"],"race_id":original.get("id"),"pick":pick,"winner":winner,
       "winner_mark":marks.get(winner),"pick_finish":order.index(pick)+1 if pick in order else None,
       "observed_starts":{"pick":selected.get("observedStarts"),"winner":actual.get("observedStarts")},
       "winner_stronger_raw_features":[key for key in FEATURES if selected["featureValues"].get(key) is not None and actual["featureValues"].get(key) is not None and float(actual["featureValues"][key])>float(selected["featureValues"][key])],
       "model_contributions_favoring_wrong_pick":contributions[:7],
       "missing_features":missing,"scenarios":scenarios}
  miss_cases.append(row)
  print("MISS_DETAIL",json.dumps(row,ensure_ascii=False,separators=(",",":")),flush=True)
print("MISS_ROOT_CAUSE_SUMMARY",json.dumps({"scored":tot["scored"],"wins":tot["hits"],"misses":tot["misses"],"no_marks":tot["no_marks"],"other_status":dict(tot),
 "winner_raw_feature_more_often":win_adv.most_common(20),"model_top3_wrong_pick_positive_drivers":top_model_errors.most_common(20),
 "unscorable_by_date":dict(missing_by_day),
 "integrity_warning":"Postrace-saved snapshots: historical reproduction only, input field timestamps not verified."},ensure_ascii=False),flush=True)
if len(miss_cases)<5:raise SystemExit("Insufficient miss cases for diagnostic audit")
