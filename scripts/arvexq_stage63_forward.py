#!/usr/bin/env python3
"""Freeze or check local shadow receipts; never certifies independent pre-off."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage63.forward import freeze, verify

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("freeze","verify"))
    p.add_argument("--plan",required=True)
    p.add_argument("--input",required=True,help="Saved race for freeze; receipt for verify")
    p.add_argument("--output",help="New receipt path; must not already exist")
    a=p.parse_args()
    plan=json.loads(Path(a.plan).read_text())
    data=json.loads(Path(a.input).read_text())
    if a.action=="freeze":
        if not a.output:p.error("--output is required for freeze")
        result=freeze(a.output,data,plan)
    else:
        result=verify(data,plan)
    print(json.dumps(result,ensure_ascii=False,indent=2))
