#!/usr/bin/env python3
"""Reproduce Stage62 and run seven labelled NAR shadow comparisons offline."""
import argparse
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage63.experiment import ARMS, predict
from arvexq.research.stage63.forward import protocol, write_once


def rows(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def run(source, labels_path, comparison_path, output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source) as z:
        races = json.loads(z.read("forward-inputs.json"))
    if len({r["id"] for r in races})!=len(races):
        raise ValueError("duplicate race IDs")
    label_rows = rows(labels_path)
    labels = {r["race_id"]:r for r in label_rows}
    old_rows = rows(comparison_path)
    old = {r["race_id"]:r for r in old_rows}
    if len(labels)!=len(label_rows) or len(old)!=len(old_rows) or set(labels)!=set(old):
        raise ValueError("duplicate or mismatched labels")
    details, coverage = [], []
    reproduced = 0
    for race in races:
        for arm in ARMS:
            prediction = predict(race,arm)
            coverage.append({"race_id":race["id"],"arm":arm,"status":prediction["status"],
                             "missing_ability":prediction.get("missingAbility",[]),
                             "missing_style":prediction.get("missingStyle",[])})
            if prediction["status"]!="research-only":
                if arm in ("baseline","recent5","recent5_shrunk") and race["id"] in old:
                    raise ValueError("previously eligible race dropped")
                continue
            if race["id"] not in labels:
                raise ValueError("eligible race has no authoritative evaluation")
            label = labels[race["id"]]
            actual = tuple(int(n) for n in label["actual"].split("-"))
            win = prediction["probabilities"]
            if len(set(actual))!=3 or any(n not in win for n in actual) or actual[0]!=int(label["first_actual"]):
                raise ValueError("invalid outcome roster")
            ranked = sorted(win,key=lambda n:(-win[n],n))
            hit = actual in prediction["tickets"]
            payout = int(label["trifecta_payout"])
            if payout<=0:
                raise ValueError("missing/invalid payout")
            record = {"race_id":race["id"],"circuit":"nar","date":race["date"],"arm":arm,
                      "winner_rank":ranked.index(actual[0])+1,
                      "logloss":-math.log(win[actual[0]]),
                      "brier":sum((p-int(n==actual[0]))**2 for n,p in win.items()),
                      "trifecta_hit":int(hit),"stake_yen":100*len(prediction["tickets"]),
                      "return_yen":payout if hit else 0}
            details.append(record)
            if arm in ("baseline","recent5","recent5_shrunk"):
                previous = old[race["id"]]
                for key,new in (("winner_rank",record["winner_rank"]),
                                ("ticket_hit",record["trifecta_hit"]),
                                ("return_yen",record["return_yen"])):
                    if int(previous[arm+"_"+key])!=new:
                        raise ValueError("Stage62 mismatch "+race["id"]+" "+arm+" "+key)
                if abs(float(previous[arm+"_logloss"])-record["logloss"])>1e-7:
                    raise ValueError("Stage62 probability mismatch")
                reproduced += 1
    summaries = []
    for arm in ARMS:
        records = [r for r in details if r["arm"]==arm]
        n = len(records)
        stake = sum(r["stake_yen"] for r in records)
        returned = sum(r["return_yen"] for r in records)
        largest = sum(sorted((r["return_yen"] for r in records),reverse=True)[:2])
        summaries.append({"arm":arm,"races":n,"unscored":len(races)-n,
                          "winner_top1":sum(r["winner_rank"]==1 for r in records),
                          "winner_top3":sum(r["winner_rank"]<=3 for r in records),
                          "mean_logloss":statistics.mean(r["logloss"] for r in records) if n else None,
                          "mean_brier":statistics.mean(r["brier"] for r in records) if n else None,
                          "trifecta_hits":sum(r["trifecta_hit"] for r in records),
                          "stake_yen":stake,"return_yen":returned,
                          "roi_pct":100*returned/stake if stake else None,
                          "top2_return_share":largest/returned if returned else None,
                          "independent":False})
    report = {"schema":"arvexq-stage63-retrospective-1","sourceSha256":sha256(Path(source).read_bytes()).hexdigest(),
              "labelSha256":sha256(Path(labels_path).read_bytes()).hexdigest(),
              "stage62ComparisonSha256":sha256(Path(comparison_path).read_bytes()).hexdigest(),
              "stage62ReproducedRaceArms":reproduced,
              "nar":summaries,"jra":{"status":"not-connected","evaluatedRaces":0},
              "independentlyVerifiedRaces":0,"productionChanged":False,
              "limitations":["Same previously examined 2026-10-16 development data.",
                             "Seven comparisons are exploratory, no best-arm selection.",
                             "Local original capturedAt is not independent preoff proof.",
                             "No calibrated scenario occurrence or winning probabilities."]}
    for name,data in (("summary.json",report),("coverage.json",coverage)):
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    with (output/"race_comparisons.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f,fieldnames=list(details[0]))
        writer.writeheader();writer.writerows(details)
    write_once(output/"forward_plan.json",protocol(r["id"] for r in races))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--labels",required=True)
    p.add_argument("--stage62-comparison",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    run(a.source,a.labels,a.stage62_comparison,a.output)
