#!/usr/bin/env python3
"""Paired retrospective comparison; not pre-off validated."""
import base64,gzip,hashlib,json,math
from pathlib import Path
from collections import defaultdict
from datetime import date,timedelta
from scripts.arvexq_current_prediction_audit import api_json,finish_order
from arvexq.prediction.factor_model import rank_factor_model
from arvexq.research.no_sectional_candidate import score

def main():
    outcomes={}
    for offset in range(7):
        day=(date(2026,10,7)+timedelta(days=offset)).isoformat()
        for d in api_json("https://kraiz-api.4b89h4fydd.workers.dev/api/day?date="+day+"&details=1").get("details") or []:
            order=finish_order(d)
            if len(order)>=3:outcomes[(str(d.get("date")),str(d.get("id")))]=order
    metrics=defaultdict(lambda:dict(n=0,wins=0,top3=0,loss=0.))
    excluded=0
    for p in sorted(Path("arvexq/ui/static/saved-snapshots").glob("*.json")):
        envelope=json.loads(p.read_text())
        if "gzipBase64" not in envelope:continue
        raw=gzip.decompress(base64.b64decode(envelope["gzipBase64"]))
        if hashlib.sha256(raw).hexdigest()!=envelope.get("sha256"):raise ValueError("SHA256 mismatch")
        race=json.loads(raw)
        order=outcomes.get((str(race.get("date")),str(race.get("id"))))
        if not order:continue
        ranked=rank_factor_model(race.get("horses") or [],race)
        base={int(x["horse"]["horseNumber"]):float(x["score"]) for x in ranked}
        new={int(x["horse"]["horseNumber"]):score(x["horse"],race) for x in ranked}
        if len(base)<3 or order[0] not in base or any(v is None for v in new.values()):
            excluded+=1
            continue
        for name,vals in (("current",base),("noSectional",new)):
            order_pred=sorted(vals,key=lambda n:(-vals[n],n))
            weights={n:math.exp(5*(v-max(vals.values()))) for n,v in vals.items()}
            probability=weights[order[0]]/sum(weights.values())
            m=metrics[name]
            m["n"]+=1;m["wins"]+=int(order_pred[0]==order[0]);m["top3"]+=int(order[0] in order_pred[:3])
            m["loss"]+=-math.log(max(probability,1e-15))
    result={"metrics":{k:{**m,"top1Rate":m["wins"]/m["n"],"top3Rate":m["top3"]/m["n"],"meanLogLoss":m["loss"]/m["n"]} for k,m in metrics.items() if m["n"]},
            "excluded":excluded,"note":"retrospective and possibly post-off snapshots; common arbitrary temperature, not calibrated probabilities"}
    print("NO_SECTIONAL_RESULT="+json.dumps(result))
    Path("research-output").mkdir(exist_ok=True)
    Path("research-output/no-sectional.json").write_text(json.dumps(result,indent=2))
if __name__=="__main__":main()
