#!/usr/bin/env python3
"""Read-only existing public day API probe. Never logs raw race data."""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

base=os.environ.get("ARVEXQ_API_URL","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
yesterday=(datetime.now(timezone(timedelta(hours=9))).date()-timedelta(days=1)).isoformat()
url=base+"/api/day?"+urlencode({"date":yesterday,"details":"1"})
req=urllib.request.Request(url,headers={"User-Agent":"ARVEXQ-Analytics-ReadOnly/1.0","Accept":"application/json"},method="GET")
try:
    with urllib.request.urlopen(req,timeout=45) as response:
        obj=json.loads(response.read(20_000_000))
except urllib.error.HTTPError as exc:
    raise SystemExit("D1_DAY_PROBE_HTTP_"+str(exc.code)) from None
except Exception as exc:
    raise SystemExit("D1_DAY_PROBE_"+type(exc).__name__) from None
if not isinstance(obj,dict) or not isinstance(obj.get("details"),list):
    raise SystemExit("D1_DAY_PROBE_UNEXPECTED_SCHEMA")
print("D1_PUBLIC_DAY_READ_OK", "date="+yesterday, "detail_count="+str(len(obj["details"])), "no_writes=true")
