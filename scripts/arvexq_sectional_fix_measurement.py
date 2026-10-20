#!/usr/bin/env python3
"""Compare measured old/new history normalization over sealed archive copies."""
import base64
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from arvexq.components.item_182.history import normalize_run
from arvexq.prediction.past_performance import observed_runs

def audit():
    totals=Counter()
    for path in Path("arvexq/ui/static/saved-snapshots").glob("*.json"):
        obj=json.loads(path.read_text())
        if "gzipBase64" not in obj:
            continue
        raw=gzip.decompress(base64.b64decode(obj["gzipBase64"],validate=True))
        if hashlib.sha256(raw).hexdigest()!=obj["sha256"]:
            raise ValueError("hash mismatch")
        race=json.loads(raw)
        circuit=str(race.get("circuit") or "unknown")
        totals["races"]+=1
        totals[circuit+"Races"]+=1
        for horse in race.get("horses") or []:
            if not isinstance(horse,dict):
                continue
            totals["horses"]+=1
            totals[circuit+"Horses"]+=1
            runs=observed_runs(horse,race,limit=5)
            totals["runs"]+=len(runs)
            for run in runs:
                n=normalize_run(run)
                if n.get("last3fRank") is not None:
                    totals["sectionalRankAvailable"]+=1
                    totals[circuit+"SectionalRankAvailable"]+=1
                if n.get("last3fPercentile") is not None:
                    totals["sectionalPercentileAvailable"]+=1
                if n.get("margin") is not None:
                    totals["marginAvailable"]+=1
                if run.get("last3fRank") is not None or run.get("last600Rank") is not None or run.get("上がり順位") is not None:
                    totals["sectionalRankOriginalRaw"]+=1
    result={"counts":dict(totals),"scope":"archived snapshot history, not verified preoff timestamp","note":"Availability only, never claim model accuracy benefit."}
    Path("research-output").mkdir(exist_ok=True)
    Path("research-output/sectional-availability.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print("SECTIONAL_AVAILABILITY="+json.dumps(result,ensure_ascii=False))

if __name__=="__main__":
    audit()
