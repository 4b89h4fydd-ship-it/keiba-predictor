#!/usr/bin/env python3
"""Explain why the existing learned model has no trainable historical races.
Read-only. Same existing day API, result labels used only for training eligibility.
"""
import json,os,urllib.parse,urllib.request
from collections import Counter
from datetime import datetime,timedelta,date
from arvexq.prediction.learned_scenarios import race_evidence,race_family
BASE=os.getenv("ARVEXQ_API_BASE","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
END=date.fromisoformat(os.getenv("ARVEXQ_END_DATE","2026-10-21"))
DAYS=int(os.getenv("ARVEXQ_DAYS","7"))
out={"中央":Counter(),"地方":Counter()}
for i in range(DAYS-1,-1,-1):
 day=(END-timedelta(days=i)).isoformat()
 req=urllib.request.Request(BASE+"/api/day?"+urllib.parse.urlencode({"date":day,"details":1}),headers={"user-agent":"ARVEXQ-research-train-eligibility/1"})
 with urllib.request.urlopen(req,timeout=55) as r: details=json.load(r).get("details") or []
 for d in details:
  c=d.get("circuit")
  if c not in out:continue
  a=out[c];a["finalized_races"]+=1
  if (d.get("result") or {}).get("status")!="確定":a["not_final"]+=1;continue
  if race_family(d)!="flat":a["non_flat"]+=1;continue
  rows=race_evidence(d)
  a["flat_result_races"]+=1
  if len(rows)<3:a["fewer_than_three_runners"]+=1;continue
  if any(not r.get("observedStarts") for r in rows):a["missing_observed_history"]+=1;continue
  labels=[x for x in (d.get("result") or {}).get("finishers") or [] if isinstance(x,dict)]
  numbers={x.get("horseNumber") for x in labels}
  roster={x.get("horseNumber") for x in rows}
  if numbers!=roster or len(labels)!=len(rows):a["incomplete_result_field"]+=1;continue
  a["potentially_trainable"]+=1
for circuit,a in out.items(): print("EXISTING_LEARNER_INPUT_ELIGIBILITY",json.dumps({"circuit":circuit,**dict(a)},ensure_ascii=False))
