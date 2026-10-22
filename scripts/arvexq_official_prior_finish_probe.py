#!/usr/bin/env python3
"""Read-only official NAR prior-result probe for existing finish=0 observations.
Uses app._nar_official_result_fast, the existing official historical result path.
Never fills unknown rankings, never changes live data or forecasts.
"""
import json
from collections import Counter
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import scrub_for_replay,finish_order
from arvexq.prediction.learned_scenarios import active_horses,race_family
from arvexq.prediction.past_performance import observed_runs
from arvexq.ingest.full_career import merge_career
import app

totals=Counter()
examples=[]
cache={}
for d in ("2026-10-17","2026-10-18"):
 for race in day(d):
  if race.get("circuit")!="地方" or race_family(race)!="flat" or (race.get("result") or {}).get("status")!="確定":continue
  clean=scrub_for_replay(race,d)
  for horse in active_horses(clean):
   if observed_runs(horse,clean,limit=None):continue
   raw=merge_career(horse.get("allPastRuns"),horse.get("recentRaces"),d)
   broken=[x for x in raw if x.get("finish") in (0,"0",None,"") and x.get("date") and x.get("track") and x.get("raceNumber")]
   if not broken:continue
   totals["malformed_horses"]+=1
   target=broken[0]
   at,track,race_no=target["date"],target["track"],int(target["raceNumber"])
   key=(at,track,race_no)
   if key not in cache:
    try:
     cache[key]=app._nar_official_result_fast({"date":at,"track":track,"raceNumber":race_no,
       "horses":[{"name":horse.get("name"),"horseNumber":target.get("horseNumber") or 0}]})
    except Exception as exc:
     cache[key]={"error":type(exc).__name__}
   outcome=cache[key]
   totals["prior_race_requested"]+=1
   if not isinstance(outcome,dict) or outcome.get("error"):
    totals["fetch_failed"]+=1;continue
   finishers=outcome.get("finishers") or []
   if not finishers:totals["prior_result_empty"]+=1;continue
   exact=[x for x in finishers if str(x.get("name") or "").strip()==str(horse.get("name") or "").strip()]
   if len(exact)!=1:
    totals["identity_no_unique_match"]+=1;continue
   found=exact[0]
   finish=found.get("finish")
   if type(finish)!=int or not 1<=finish<=len(finishers):
    totals["finish_not_verified"]+=1;continue
   totals["verified_exact_identity_finish"]+=1
   examples.append({"target_race":race.get("id"),"horse":horse.get("name"),"horse_no":horse.get("horseNumber"),
     "is_target_winner":horse.get("horseNumber")==finish_order(race)[0],
     "prior":{"date":at,"track":track,"race_number":race_no,"known_finish":0},
     "official_prior_finish":finish,"official_rows":len(finishers)})
print("OFFICIAL_PRIOR_FINISH_PROBE",json.dumps({"counts":dict(totals),"matches":examples},ensure_ascii=False),flush=True)
