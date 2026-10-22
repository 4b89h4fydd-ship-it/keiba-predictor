#!/usr/bin/env python3
"""Inspect original compressed ARVEXQ prediction envelopes, read-only; no picks inferred."""
import base64
import collections
import gzip
import hashlib
import json
import os
import duckdb

if not os.getenv("motherduck_token"):
    raise SystemExit("Missing MotherDuck token")
con=duckdb.connect("md:my_db",config={"access_mode":"READ_ONLY"})
try:
    rows=con.execute("""SELECT race_id, CAST(snapshot_json AS VARCHAR) FROM
      my_db.arvexq_analytics.race_snapshots
      WHERE json_array_length(json_extract(snapshot_json,'$.result.finishers')) >= 3
      ORDER BY race_date DESC, race_id LIMIT 60""").fetchall()
finally:
    con.close()
top=collections.Counter()
predtypes=collections.Counter()
pred_keys=collections.Counter()
bet_keys=collections.Counter()
horse_keys=collections.Counter()
bad=0
valid=0
for rid,txt in rows:
    obj=json.loads(txt)
    ref=obj.get("arvexqFullPayload") or {}
    try:
        if ref.get("version")!="arvexq-full-payload-v1": raise ValueError("unexpected codec")
        raw=gzip.decompress(base64.b64decode(ref["gzipBase64"],validate=True))
        if len(raw)!=ref["bytes"] or hashlib.sha256(raw).hexdigest()!=ref["sha256"]:
            raise ValueError("compressed payload digest mismatch")
        full=json.loads(raw)
        valid+=1
    except Exception:
        bad+=1
        continue
    top.update(full.keys())
    pre=full.get("preRacePrediction")
    predtypes[type(pre).__name__]+=1
    if isinstance(pre,dict):
        pred_keys.update(pre.keys())
        horses=pre.get("horses")
        if isinstance(horses,list) and horses and isinstance(horses[0],dict):
            horse_keys.update(horses[0].keys())
    bet=full.get("preRaceBet")
    if isinstance(bet,dict):bet_keys.update(bet.keys())
print("ORIGINAL_SNAPSHOT_DECODE",json.dumps({"checked":len(rows),"verified":valid,"decode_errors":bad}))
print("ORIGINAL_PREDICTION_SCHEMA",json.dumps({"preRacePrediction_types":predtypes,"preRacePrediction_keys":pred_keys,"preRacePrediction_horse_keys":horse_keys,"preRaceBet_keys":bet_keys,"relevant_root_keys":{k:v for k,v in top.items() if any(t in k.lower() for t in ("predict","bet","pick","model","morning","revision"))}},ensure_ascii=False,default=dict))
if bad:raise SystemExit("Snapshot integrity errors")
