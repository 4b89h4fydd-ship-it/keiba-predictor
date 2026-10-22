#!/usr/bin/env python3
"""Audit *why* the existing original provisional learner sees zero past starts.
Same seven API days as previous walk-forward. Read-only. Does not substitute
post-event features for true pre-off evidence.
"""
import json
from collections import Counter,defaultdict
from datetime import date,timedelta
from arvexq.prediction.learned_scenarios import active_horses,race_family
from arvexq.prediction.past_performance import observed_runs,_date,_number
from arvexq.ingest.full_career import merge_career
from scripts.arvexq_provisional_real_pilot import day
from scripts.arvexq_current_prediction_audit import finish_order,scrub_for_replay

dates=[(date(2026,10,15)+timedelta(days=i)).isoformat() for i in range(7)]
byc=defaultdict(Counter);samples=defaultdict(list);specials=defaultdict(list)
for daystr in dates:
 for race in day(daystr):
  circuit=race.get("circuit")
  if circuit not in ("中央","地方") or race_family(race)!="flat":continue
  if (race.get("result") or {}).get("status")!="確定" or not finish_order(race):continue
  clean=scrub_for_replay(race,daystr)
  winner=finish_order(race)[0]
  horses=active_horses(clean)
  for horse in horses:
   out=byc[circuit]
   out["active_horses"]+=1
   if horse.get("debutNoHistory"):out["explicit_debut_flag"]+=1
   past=observed_runs(horse,clean,limit=None)
   if past:out["usable_history"]+=1;continue
   out["missing_observed_history"]+=1
   if int(horse["horseNumber"])==winner:out["missing_winner_history"]+=1
   raw={k:horse.get(k) for k in ("recentRaces","allPastRuns","pastRaces","history","runs")}
   raw_counts={k:len(v) for k,v in raw.items() if isinstance(v,list)}
   raw_items=[v for values in raw.values() if isinstance(values,list) for v in values if isinstance(v,dict)]
   valid_date=0;prior_date=0;fieldsize=0;finish=0;eligible=0
   for run in raw_items:
    dt=_date(run.get("date") or run.get("raceDate") or run.get("日付"))
    if dt:valid_date+=1
    if dt and dt.isoformat()<daystr:
     prior_date+=1
     size=_number(run.get("fieldSize") or run.get("runners") or run.get("頭数"))
     pos=_number(run.get("finish") or run.get("finishPosition") or run.get("着順"))
     if size and size>=2:fieldsize+=1
     if pos and pos>=1:finish+=1
     if size and size>=2 and pos and 1<=pos<=size:eligible+=1
   reason=("archive_only" if isinstance(horse.get("careerArchive"),dict) and not raw_items else
     "no_raw_history" if not raw_items else
     "no_valid_dates" if not valid_date else
     "all_dates_current_or_future" if not prior_date else
     "missing_fieldsize_or_finish" if not eligible else
     "dropped_during_normalization_or_family")
   out["reason_"+reason]+=1
   if int(horse["horseNumber"])==winner:out["winner_reason_"+reason]+=1
   sink=specials[circuit] if reason=="missing_fieldsize_or_finish" else samples[circuit]
   if len(sink)<22:
    sink.append({"date":daystr,"race":race.get("id"),"horseNo":horse["horseNumber"],
     "is_winner":horse["horseNumber"]==winner,"reason":reason,"raw_counts":raw_counts,
     "counts":{"raw":len(raw_items),"dated":valid_date,"prior":prior_date,"fieldsize":fieldsize,"finish":finish,"eligible":eligible},
     "has_archive":isinstance(horse.get("careerArchive"),dict),
     "archive_stored_runs":(horse.get("careerArchive") or {}).get("storedRunCount") if isinstance(horse.get("careerArchive"),dict) else None,
     "career_audit":(horse.get("_careerHistoryAudit") or {}).get("status"),
     "debut_flag":bool(horse.get("debutNoHistory")),
     "prior_raw_keys":[sorted(list(x.keys()))[:40] for x in raw_items[:2]],
     "prior_raw_example":[{k:x.get(k) for k in ("date","raceDate","fieldSize","runners","頭数","finish","finishPosition","着順","rank","status","取消","競走中止") if k in x} for x in raw_items[:2]]})
for circuit in ("中央","地方"):
 print("HISTORY_CAUSE_SUMMARY",json.dumps({"circuit":circuit,**dict(byc[circuit])},ensure_ascii=False),flush=True)
 print("HISTORY_CAUSE_EXAMPLES",json.dumps({"circuit":circuit,"examples":samples[circuit]},ensure_ascii=False),flush=True)
 print("HISTORY_CAUSE_MALFORMED",json.dumps({"circuit":circuit,"examples":specials[circuit]},ensure_ascii=False),flush=True)
