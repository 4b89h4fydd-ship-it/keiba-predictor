#!/usr/bin/env python3
"""Diagnose existing learner's historical data; read-only existing /api/day.
No inference on current race results and no changes to prediction model.
"""
import collections,json,os,urllib.parse,urllib.request
from datetime import date,timedelta
from arvexq.prediction.learned_scenarios import race_evidence,race_family,active_horses
from arvexq.prediction.past_performance import observed_runs
from arvexq.ingest.full_snapshot_codec import unpack_detail
BASE=os.getenv("ARVEXQ_API_BASE","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
END=date.fromisoformat(os.getenv("ARVEXQ_END_DATE","2026-10-21"))
DAYS=int(os.getenv("ARVEXQ_DAYS","7"))
for offset in range(DAYS-1,-1,-1):
 day=(END-timedelta(days=offset)).isoformat()
 req=urllib.request.Request(BASE+"/api/day?"+urllib.parse.urlencode({"date":day,"details":1}),headers={"user-agent":"ARVEXQ-existing-history-audit/1"})
 try:
  with urllib.request.urlopen(req,timeout=65) as r: batch=json.load(r).get("details") or []
 except Exception as e:
  print("HISTORY_SOURCE_DAY_ERROR",day,type(e).__name__);continue
 counter=collections.defaultdict(collections.Counter)
 for thin in batch:
  d=unpack_detail(thin) if "arvexqFullPayload" in thin else thin
  c=d.get("circuit") or "unknown"
  if c not in ("中央","地方") or (d.get("result") or {}).get("status")!="確定" or race_family(d)!="flat":continue
  a=counter[c];a["races"]+=1
  horse=active_horses(d)
  a["horses"]+=len(horse)
  for h in horse:
   keys=["allPastRuns","recentRaces","pastRaces","history","runs"]
   if any(isinstance(h.get(k),list) and h[k] for k in keys):a["horses_with_visible_history"]+=1
   if isinstance(h.get("careerArchive"),dict):a["horses_with_career_archive"]+=1
   if isinstance(h.get("careerTransport"),dict):a["horses_with_transport"]+=1
   runs=observed_runs(h,d,limit=None)
   if runs:a["horses_with_valid_observed_runs"]+=1
   else:a["horses_without_valid_observed_runs"]+=1
   if runs and not a["sample_observed"]:a["sample_observed"]=1
   if not runs and any(isinstance(h.get(k),list) and h[k] for k in keys):a["visible_but_invalid"]+=1
  if any(not z.get("observedStarts") for z in race_evidence(d)):a["races_missing_learner_history"]+=1
 for circuit,counts in counter.items(): print("HISTORY_INPUT_DIAGNOSTIC",json.dumps({"date":day,"circuit":circuit,**dict(counts)},ensure_ascii=False))
