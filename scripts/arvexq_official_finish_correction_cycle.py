#!/usr/bin/env python3
"""ARVEXQ research cycle: existing official NAR result fixes only finish=0.
Never guesses horse finishes; all other predictors, models and routes unchanged.
Chronological 7 dates, 4 validation + 2 untouched holdout, before target result.
"""
import copy,json
from collections import Counter
from datetime import date,timedelta
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import fit_model,race_family,active_horses
from arvexq.prediction.new_forecast import build_forecast
from arvexq.ingest.full_career import merge_career
import app
dates=[(date(2026,10,15)+timedelta(days=i)).isoformat() for i in range(7)]
data={d:day(d) for d in dates}
official_cache={}
def rescue(original):
 detail=copy.deepcopy(original)
 count=Counter()
 for horse in active_horses(detail):
  rows=merge_career(horse.get("allPastRuns"),horse.get("recentRaces"),detail["date"])
  zero=[x for x in rows if x.get("finish") in (0,"0") and x.get("date") and x.get("track") and x.get("raceNumber")]
  if not zero:continue
  changed={}
  for run in zero:
   day=str(run["date"]);track=str(run["track"]);number=int(run["raceNumber"])
   if day>=detail["date"]:continue
   key=(day,track,number)
   if key not in official_cache:
    try:official_cache[key]=app._nar_official_result_fast({"date":day,"track":track,"raceNumber":number,
      "horses":[{"name":horse.get("name"),"horseNumber":run.get("horseNumber") or 0}]})
    except Exception as exc:official_cache[key]={"error":type(exc).__name__}
   result=official_cache[key]
   if not isinstance(result,dict) or not isinstance(result.get("finishers"),list):count["unavailable"]+=1;continue
   finishers=result["finishers"]
   exact=[x for x in finishers if str(x.get("name") or "").strip()==str(horse.get("name") or "").strip()]
   if len(exact)!=1:count["not_unique_name"]+=1;continue
   pos=exact[0].get("finish")
   if type(pos)!=int or not 1<=pos<=len(finishers):count["invalid_official_finish"]+=1;continue
   changed[day]=(track,number,pos)
   count["verified_finish"]+=1
  if not changed:continue
  # Correct only observed finish=0 for exactly the same prior date, track and race no.
  for field in ("allPastRuns","recentRaces"):
   source=horse.get(field)
   if not isinstance(source,list):continue
   for item in source:
    if not isinstance(item,dict) or item.get("finish") not in (0,"0"):continue
    found=changed.get(str(item.get("date") or item.get("raceDate") or ""))
    if found and str(item.get("track"))==found[0] and int(item.get("raceNumber") or 0)==found[1]:
     item["finish"]=found[2]
     item["researchOfficialPriorFinishVerified"]=True
 return detail,count
summary=[]
history=[]
for d in dates:
 original_batch=data[d]
 previous=[r for r in history if r.get("circuit")=="地方"]
 try:model=fit_model(previous,circuit="地方")
 except ValueError:
  history.extend(original_batch);continue
 scores={k:Counter() for k in ("baseline","verified_prior_finish")}
 day_cause=Counter();examples=[]
 for original in original_batch:
  if original.get("circuit")!="地方" or race_family(original)!="flat" or (original.get("result") or {}).get("status")!="確定":continue
  order=finish_order(original)
  if not order:continue
  plain=scrub_for_replay(original,d)
  fixed,audit=rescue(plain)
  day_cause.update(audit)
  picks={}
  for label,detail in (("baseline",plain),("verified_prior_finish",fixed)):
   try:
    out=build_forecast(detail,model)
    if out.get("predictionStatus")!="candidate-analysis":scores[label]["unscorable"]+=1;continue
    head=[int(x["horseNumber"]) for x in out.get("horses") or [] if (x.get("integratedEvaluation") or {}).get("mark")=="◎"]
    if len(head)!=1:scores[label]["unscorable"]+=1;continue
    picks[label]=head[0]
   except (ValueError,TypeError,KeyError,OverflowError):
    scores[label]["error"]+=1
  # Compare actual finish only after both existing-model predictions complete.
  for label,pick in picks.items():
   scores[label]["scored"]+=1
   scores[label]["hits"]+=int(pick==order[0])
   scores[label]["top3"]+=int(pick in order[:3])
  if audit["verified_finish"]:
   day_cause["races_with_verified_prior_finishes"]+=1
   if len(examples)<10:
    examples.append({"race":original["id"],"original_pick":picks.get("baseline"),
     "repaired_pick":picks.get("verified_prior_finish"),"winner":order[0],
     "number_of_prior_finishes_verified":audit["verified_finish"]})
 phase="holdout" if d>="2026-10-20" else "validation"
 report={"day":d,"phase":phase,"models":{k:dict(v) for k,v in scores.items()},"audit":dict(day_cause),"examples":examples}
 summary.append(report)
 print("OFFICIAL_FINISH_CYCLE_DAY",json.dumps(report,ensure_ascii=False),flush=True)
 history.extend(original_batch)
def totals(phase,label):
 z=Counter()
 for r in summary:
  if r["phase"]==phase:z.update(r["models"][label])
 return {k:z[k] for k in ("scored","hits","top3","unscorable","error")}
validate={m:totals("validation",m) for m in ("baseline","verified_prior_finish")}
holdout={m:totals("holdout",m) for m in ("baseline","verified_prior_finish")}
base=validate["baseline"];alt=validate["verified_prior_finish"]
candidate=bool(base["scored"] and alt["scored"] and alt["hits"]*base["scored"]>base["hits"]*alt["scored"] and alt["error"]==base["error"])
hb=holdout["baseline"];ha=holdout["verified_prior_finish"]
confirmed=bool(candidate and hb["scored"] and ha["scored"] and ha["hits"]*hb["scored"]>hb["hits"]*ha["scored"] and ha["error"]==hb["error"])
print("OFFICIAL_FINISH_CYCLE_FINAL",json.dumps({"validation":validate,"holdout":holdout,
 "verified_history_by_day":{r["day"]:r["audit"].get("verified_finish",0) for r in summary},
 "validation_candidate":candidate,"holdout_improved":confirmed,
 "decision":"research_only_no_production" if confirmed else "not_proven_continue_research",
 "warning":"Historical after-event records can have other mutable features; no confirmed pre-off snapshot as-of guarantee."},ensure_ascii=False),flush=True)
if not hb["scored"]:raise SystemExit("No held-out runs")
