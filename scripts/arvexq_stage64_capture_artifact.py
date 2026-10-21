#!/usr/bin/env python3
"""Read existing saved-data artifacts; freeze all requested-circuit race cards."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage64.witness import GitHubArtifacts, read_witness, instant
from arvexq.research.stage64.protocol import freeze_batch, check_plan, JST
from arvexq.research.stage64.circuits import circuit
from scripts.arvexq_stage64_auto_capture import require_complete_saved_details


def saved_race_rows(source):
    """Retain the original array contract; reject partial saved Prefetch bundles."""
    if isinstance(source, dict):
        rows = source.get("details")
        if not isinstance(rows, list):
            raise ValueError("saved source must be a race array or details array")
        require_complete_saved_details(source, rows)
        return rows
    if not isinstance(source, list):
        raise ValueError("saved source must be a race array or details array")
    return source


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-artifact",type=int,required=True)
    p.add_argument("--source-member",required=True)
    p.add_argument("--plan-artifact",type=int,required=True)
    p.add_argument("--circuit",choices=("jra","nar"),required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    client=GitHubArtifacts()
    plan_bundle,anchor=read_witness(client,a.plan_artifact,before=datetime.now(timezone.utc))
    plan=plan_bundle["plan"];check_plan(plan)
    if plan["circuit"]!=a.circuit:raise ValueError("wrong circuit plan")
    opening=datetime.fromisoformat(plan["startDate"]+"T00:00:00").replace(tzinfo=JST)
    if instant(anchor["serverObservedBy"])>=opening:
        raise ValueError("plan was not preregistered")
    source,source_anchor=read_witness(client,a.source_artifact,before=datetime.now(timezone.utc),
                                     source_member=a.source_member)
    rows=saved_race_rows(source)
    races=[r for r in rows if circuit(r)==a.circuit]
    batch=freeze_batch(a.output,races,plan)
    print(json.dumps({"frozenRaces":len(batch["cohort"]),"source":source_anchor,
                      "provenance":"awaiting immutable forecast artifact upload and completed workflow witness",
                      "productionChanged":False},ensure_ascii=False))
