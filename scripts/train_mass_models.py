#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.mass_model_export import export_all_runtimes
from arvexq.prediction.mass_model_training import train_all_heads, _training_circuit


def load_jsonl(path: str | Path) -> list[dict]:
    rows=[]
    with Path(path).open("r",encoding="utf-8") as fh:
        for line in fh:
            line=line.strip()
            if not line:
                continue
            row=json.loads(line)
            if isinstance(row,dict):
                rows.append(row)
    return rows


def main() -> int:
    parser=argparse.ArgumentParser(description="Train isolated ARVEXQ mass-feature challenger heads")
    parser.add_argument("dataset",help="Frozen training JSONL from export_mass_training_dataset.py")
    parser.add_argument("model_dir",help="Directory for CatBoost/vectorizer artifacts")
    parser.add_argument("runtime_dir",help="Directory for standalone runtime exports")
    parser.add_argument(
        "--circuit", choices=("jra", "nar"), required=True,
        help="Mandatory circuit of this single-circuit frozen dataset; no mixed training",
    )
    args=parser.parse_args()

    rows=load_jsonl(args.dataset)
    try:
        actual_circuit = _training_circuit(rows)
    except ValueError as exc:
        raise SystemExit(f"refuse mixed or unlabelled training: {exc}") from exc
    if actual_circuit != args.circuit:
        raise SystemExit(
            f"refuse training: requested {args.circuit}, frozen rows are {actual_circuit}"
        )
    races=len({str(r.get("raceId") or "") for r in rows})
    if races<40:
        raise SystemExit(f"refuse training: only {races} frozen races; collect more true pre-race snapshots")
    result=train_all_heads(rows,args.model_dir)
    exported=export_all_runtimes(args.model_dir,args.runtime_dir)
    print(json.dumps({"training":result,"export":exported},ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
