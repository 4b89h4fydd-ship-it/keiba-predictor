#!/usr/bin/env python3
"""Real-race trial of the EXISTING provisional forecaster, no database persistence.
Train NAR on Oct 15 only, forecast Oct 16 using scrubbed pre-race facts, then score.
"""
from __future__ import annotations
import json,urllib.request,urllib.parse,urllib.error,os
from concurrent.futures import ThreadPoolExecutor
from scripts.arvexq_fetch_d1_bundle import get_json,detail_from_response
from arvexq.ingest.full_snapshot_codec import unpack_detail
from scripts.arvexq_current_prediction_audit import evaluate_provisional_predictions
API=os.environ.get("ARVEXQ_API_BASE","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
def day(date):
 url=API+"/api/day?"+urllib.parse.urlencode({"date":date,"details":0})
 overview=get_json(url,35,4)
 rows=[x for x in (overview.get("races") or []) if isinstance(x,dict) and x.get("id")]
 def fetch(row):
  rid=str(row["id"])
  uri=API+"/api/race/"+urllib.parse.quote(rid,safe="")
  for suffix in ("","?view=display"):
   try:
    detail=detail_from_response(get_json(uri+suffix,30,4),rid)
    if detail is not None:return detail
   except Exception:pass
  raise RuntimeError("race detail unavailable for "+rid)
 with ThreadPoolExecutor(max_workers=4) as pool:
  out=list(pool.map(fetch,rows))
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
