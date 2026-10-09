#!/usr/bin/env python3
"""Offline training on multiple immutable nightly archive JSON files."""
import argparse
import json
from pathlib import Path
from arvexq.backtest.factor_weight_calibration import calibrate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("audit_files",nargs="+")
    args=parser.parse_args()
    rows=[]
    for filename in args.audit_files:
        data=json.loads(Path(filename).read_text(encoding="utf-8"))
        rows.extend(data.get("factor_weight_samples") or [])
    print(json.dumps(calibrate(rows),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
