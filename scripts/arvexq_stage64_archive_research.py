#!/usr/bin/env python3
"""Connect both circuits to real saved input and score every submitted race."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage63.forward import digest
from arvexq.research.stage64.circuits import circuit, active as is_active
from arvexq.research.stage64.pipeline import predict
from arvexq.research.stage64.protocol import ARMS, make_plan
from arvexq.research.stage64.evaluation import evaluate


def run(source, output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source) as z:
        inputs=json.loads(z.read("enriched-inputs.json"))
        forward=json.loads(z.read("forward-inputs.json"))
        comparison=json.loads(z.read("comparison.json"))
    all_ids=[r["id"] for r in inputs]
    label_rows=comparison["dataset"]
    if len(set(all_ids))!=len(all_ids) or len({r["id"] for r in label_rows})!=len(label_rows) or set(all_ids)!={r["id"] for r in label_rows}:
        raise ValueError("saved input/outcome population mismatch")
    labels={r["id"]:r for r in label_rows}
    receipts=[];results=[];coverage=[]
    for race in inputs:
        owner=circuit(race)
        predictions={arm:predict(race,expected_circuit=owner,ability_method=arm) for arm in ARMS}
        snap={"raceId":race["id"],"circuit":owner,"input":race,"predictions":predictions}
        receipts.append({"snapshot":snap,"snapshotSha256":digest(snap)})
        label=labels[race["id"]]
        active={h["horseNumber"] for h in race["horses"] if is_active(h)}
        if active!=set(label["nos"]):
            raise ValueError("saved label roster differs from input "+race["id"])
        results.append({"raceId":race["id"],"circuit":owner,"date":race["date"],
                        "status":"confirmed","orders":label["orders"],"payouts":label["payoutEntries"] or None})
        for arm,p in predictions.items():
            coverage.append({"raceId":race["id"],"circuit":owner,"date":race["date"],"arm":arm,
                             "stages":{name:item["status"] for name,item in p["stages"].items()},
                             "blockers":p["blockers"]})
    batch={"schema":"retrospective-not-a-forward-receipt","cohort":sorted(all_ids),"receipts":receipts}
    report=evaluate(batch,results)
    report["sourceSha256"]=sha256(Path(source).read_bytes()).hexdigest()
    report["sourceInputMember"]="enriched-inputs.json"
    report["inputRaceCount"]=len(inputs)
    report["retrospectiveForecastDigest"]=digest(batch)
    report["limits"]=["All dates were already part of earlier research; not untouched holdout.",
                      "Five JRA jumps races are unsupported and remain in the full-cohort denominator.",
                      "No horse-ID cross-race joins; missing history is not filled by horse name.",
                      "Full-calendar completeness and source observation times are not independently certified."]
    rows=report.pop("rows")
    (output/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    # Eligibility is identical across these three ability-only arms. Preserve
    # baseline per-runner blockers once rather than triplicating observations.
    compact=[{"raceId":r["raceId"],"circuit":r["circuit"],"date":r["date"],
              "stageStatus":r["stages"],"blockers":r["blockers"]}
             for r in coverage if r["arm"]=="baseline"]
    (output/"coverage.json").write_text(json.dumps(compact,ensure_ascii=False,separators=(",",":"))+"\n")
    with (output/"race_metrics.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # Diagnose all 11 target-date unavailable races without unsafe name joins.
    gaps=[]
    for race in forward:
        p=predict(race,expected_circuit="nar")
        if p["stages"]["tickets"]["value"] is None:
            gaps.append({"raceId":race["id"],"blockers":p["blockers"],
                         "repairStatus":"no-verified-horse-ID-link; existing source investigation required"})
    (output/"nar_forward_gaps.json").write_text(json.dumps(gaps,ensure_ascii=False,indent=2)+"\n")
    for owner in ("jra","nar"):
        plan=make_plan(owner,all_ids+[r["id"] for r in forward])
        (output/(owner+"_candidate_plan.json")).write_text(json.dumps({"plan":plan},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"byCircuit":report["byCircuit"],"narForwardUnscored":len(gaps),
                      "independentlyVerifiedPreoff":False},ensure_ascii=False,indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();run(a.source,a.output)
