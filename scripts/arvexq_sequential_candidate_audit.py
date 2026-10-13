#!/usr/bin/env python3
"""Compare research scores on the SAME final races; retrospective, not pre-off proof."""
import json
import math
import base64
import gzip
import hashlib
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
from scripts.arvexq_current_prediction_audit import api_json,finish_order,scrub_for_replay
from arvexq.prediction.factor_model import rank_factor_model
from arvexq.research.sequential_challengers import candidates

def evaluate():
    results=defaultdict(lambda: {"races":0,"top1":0,"top3":0,"logLossSum":0.})
    coverage=defaultdict(int)
    outcomes={}
    for offset in range(7):
        day=(date(2026,10,7)+timedelta(days=offset)).isoformat()
        data=api_json("https://kraiz-api.4b89h4fydd.workers.dev/api/day?date="+day+"&details=1")
        for detail in data.get("details") or []:
            order=finish_order(detail)
            if len(order)>=3:
                outcomes[(str(detail.get("date")),str(detail.get("id")))]=order
    envelopes=0
    for path in sorted(Path("arvexq/ui/static/saved-snapshots").glob("*.json")):
        envelope=json.loads(path.read_text())
        if "gzipBase64" not in envelope: continue
        raw=gzip.decompress(base64.b64decode(envelope["gzipBase64"]))
        if hashlib.sha256(raw).hexdigest()!=envelope.get("sha256"):
            raise ValueError("snapshot hash mismatch")
        detail=json.loads(raw)
        envelopes+=1
        order=outcomes.get((str(detail.get("date")),str(detail.get("id"))))
        if not order: continue
        rows=rank_factor_model(detail.get("horses") or [],detail)
        if len(rows)<3: continue
        variants={"current":{int(z["horse"]["horseNumber"]):z["score"] for z in rows}}
        for z in rows:
            n=int(z["horse"]["horseNumber"])
            for key,value in candidates(z["horse"],detail).items():
                variants.setdefault(key,{})[n]=value
        for name,values in variants.items():
            if set(values)!=set(variants["current"]) or order[0] not in values:
                coverage[name]+=1
                continue
            ranked=sorted(values,key=lambda n:(-values[n],n))
            mx=max(values.values())
            weights={n:math.exp(5*(v-mx)) for n,v in values.items()}
            p=weights[order[0]]/sum(weights.values())
            m=results[name]
            m["races"]+=1;m["top1"]+=int(ranked[0]==order[0])
            m["top3"]+=int(order[0] in ranked[:3])
            m["logLossSum"]+=-math.log(max(p,1e-15))
    return {"version":"research-retrospective-v2","inputEnvelopes":envelopes,
            "matchedResultRaces":len(outcomes),
            "results":{k:{**v,"top1Rate":v["top1"]/v["races"],
                "top3Rate":v["top3"]/v["races"],
                "meanLogLoss":v["logLossSum"]/v["races"]}
                for k,v in results.items() if v["races"]},
            "missingEvidenceByVariant":dict(coverage),
            "warning":"Retrospective snapshot inputs may contain post-race changes; not exact pre-off evidence. Different candidate coverage and fixed uncalibrated temperature. Not promotion proof."}

if __name__=="__main__":
    from sys import argv
    out=evaluate()
    Path(argv[1]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print("RESULT="+json.dumps(out,ensure_ascii=False))
