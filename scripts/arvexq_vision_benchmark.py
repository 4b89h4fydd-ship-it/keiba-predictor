#!/usr/bin/env python3
"""Evaluate anonymous tracks only against a separate independent truth file.

Example:
  python scripts/arvexq_vision_benchmark.py --prediction smoke.json \
    --truth vetted-labels.json --output metrics.json

An annotation template is not ground truth; it will NOT pass evaluation until
real observed horse boxes, stable per-horse identifiers, and an independent
review attestation have been entered by a qualified reviewer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.vision.benchmark import evaluate_labels


def template_from_video(pred: dict) -> dict:
    if not isinstance(pred.get("observedFrames"), list):
        raise ValueError("no real predictions with frame coordinates available")
    return {
        "videoSha256": pred.get("sourceVideoSha256"),
        "sourcePage": pred.get("sourcePage"),
        "annotation": {
            "method": "not-yet-reviewed",
            "reviewed": False,
            "annotator": "",
            "version": "",
            "usedModelPredictionsAsTruth": None,
        },
        "frames": [
            {"seconds": frame["seconds"], "horses": []}
            for frame in pred["observedFrames"]
        ],
        "_instructions": (
            "Independent reviewer must annotate each video frame, including "
            "horses the model failed to detect. Provide their actual bounding "
            "boxes and CONSISTENT visual horseId between frames. Do not use "
            "model track IDs as truth. Empty horses means truly zero visible "
            "horses only. Attestation must be independently signed/reviewed."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--truth", type=Path)
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    prediction = json.loads(args.prediction.read_text(encoding="utf-8"))
    if args.template == bool(args.truth):
        parser.error("Specify either --template or --truth PATH")
    if args.template:
        report = template_from_video(prediction)
    else:
        truth = json.loads(args.truth.read_text(encoding="utf-8"))
        report = evaluate_labels(prediction, truth)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "result": "unreviewed-annotation-template" if args.template else "verified-label-comparison",
        "path": str(args.output),
        "predictionApplied": False
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
