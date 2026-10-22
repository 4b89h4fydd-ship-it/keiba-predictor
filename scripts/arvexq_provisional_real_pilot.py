#!/usr/bin/env python3
"""Real-race trial of the EXISTING provisional forecaster, no database persistence.
Train NAR on Oct 15 only, forecast Oct 16 using scrubbed pre-race facts, then score.
"""
from __future__ import annotations
import json,urllib.request,urllib.parse,os
from arvexq.ingest.full_snapshot_codec import unpack_detail
from scripts.arvexq_current_prediction_audit import evaluate_provisional_predictions
API=os.environ.get("ARVEXQ_API_BASE","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
def day(date):
 url=API+"/api/day?"+urllib.parse.urlencode({"date":date,"details":1})
 req=urllib.request.Request(url,headers={"user-agent":"ARVEXQ-provisional-pilot/1","accept":"application/json"})
 with urllib.request.urlopen(req,timeout=75) as r: obj=json.load(r)
 out=[]
 for d in obj.get("details") or []:
  if isinstance(d,dict) and d.get("circuit") in ("中央","地方"):
   out.append(unpack_detail(d) if "arvexqFullPayload" in d else d)
 print("RESEARCH_SOURCE_DAY",json.dumps({"date":date,"full_races":len(out),"circuits":{c:sum(d.get("circuit")==c for d in out) for c in ("中央","地方")}},ensure_ascii=False),flush=True)
 return out
data=day("2026-10-15")+day("2026-10-16")
report=evaluate_provisional_predictions(data)
for circuit in ("中央","地方"):
 r=report[circuit]
 summary={k:r[k] for k in ("scoredRaces","winnerTop1Hits","winnerTop1Rate","noEarlierTrainedModel","missingPrediction","analysisType")}
 summary["misses"]=len(r["misses"])
 summary["first_miss"]=r["misses"][0] if r["misses"] else None
 print("REAL_PROVISIONAL_RESULT",json.dumps({"circuit":circuit,**summary},ensure_ascii=False,default=str),flush=True)
if not report["地方"]["scoredRaces"]:
 raise SystemExit("No actual provisional predictions: inspect existing output and gates")
