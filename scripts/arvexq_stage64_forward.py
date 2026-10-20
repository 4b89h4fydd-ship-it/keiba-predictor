#!/usr/bin/env python3
"""Manual research plan/freeze/verified scoring; never schedules or deploys."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage63.forward import write_once
from arvexq.research.stage64.protocol import make_plan, freeze_batch
from arvexq.research.stage64.witness import GitHubArtifacts, verify_batch
from arvexq.research.stage64.evaluation import evaluate


def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("plan","freeze","score"))
    p.add_argument("--circuit",choices=("jra","nar"))
    p.add_argument("--input",help="Known development races for plan; saved future races for freeze")
    p.add_argument("--plan");p.add_argument("--results");p.add_argument("--output",required=True)
    p.add_argument("--plan-artifact",type=int);p.add_argument("--forecast-artifact",type=int)
    a=p.parse_args()
    read=lambda path:json.loads(Path(path).read_text())
    if a.action=="plan":
        if not a.circuit or not a.input:p.error("plan requires --circuit and --input")
        development=read(a.input)
        plan=make_plan(a.circuit,[r["id"] for r in development])
        write_once(a.output,{"plan":plan})
    elif a.action=="freeze":
        if not a.plan or not a.input:p.error("freeze requires --plan and --input")
        freeze_batch(a.output,read(a.input),read(a.plan)["plan"])
    else:
        if not a.plan_artifact or not a.forecast_artifact or not a.results:
            p.error("score requires authenticated GitHub artifact IDs and --results")
        verified=verify_batch(GitHubArtifacts(),a.plan_artifact,a.forecast_artifact)
        result=evaluate(verified["batch"],read(a.results),independently_verified=True)
        result["anchors"]=verified["anchors"]
        write_once(a.output,result)
    print(json.dumps({"output":a.output,"productionChanged":False},ensure_ascii=False))

if __name__=="__main__":main()
