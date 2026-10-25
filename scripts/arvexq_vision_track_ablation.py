"""Real-video track-continuity experiment; does NOT estimate identity accuracy.

Paired observation counts compare effective sampling cadence on the SAME
licensed clip. More temporary IDs can be caused by different numbers of
detections or real motion; only independently labelled horses yield IDF1,
HOTA or switch rates. This guard prevents promoting proxy scores as truth.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare(baseline: dict, dense: dict) -> dict:
    if not baseline.get("sourceVideoSha256") or (
        baseline["sourceVideoSha256"] != dense.get("sourceVideoSha256")
    ):
        raise ValueError("video provenance mismatch")
    if not (baseline.get("sampleRateHz") == 1.0
            and dense.get("sampleRateHz") > 1.0):
        raise ValueError("expected 1 Hz baseline and denser sampled run")
    if baseline.get("testedDurationSeconds") != dense.get("testedDurationSeconds"):
        raise ValueError("sample durations must be equal")
    for record in (baseline, dense):
        if record.get("predictionApplied") is not False:
            raise ValueError("research detector cannot edit live predictions")
        if record.get("horseIdentityAccuracyKnown") is not False:
            raise ValueError("experiment lacks ground-truth horse identity")
    return {
        "version": "arvexq-track-continuity-ablation-v1",
        "sourceVideoSha256": baseline["sourceVideoSha256"],
        "durationSeconds": baseline["testedDurationSeconds"],
        "baseline1Hz": {
            "detections": baseline["horseObjectObservations"],
            "temporaryTrackIds": baseline["distinctTemporaryTrackIds"],
            "meanObservationsPerId": baseline["trackContinuityProxies"]["meanDetectionsPerTrackId"],
            "longestContinuousFrames": baseline["trackContinuityProxies"]["longestConsecutiveSampledFrames"],
        },
        "dense": {
            "rateHz": dense["sampleRateHz"],
            "detections": dense["horseObjectObservations"],
            "temporaryTrackIds": dense["distinctTemporaryTrackIds"],
            "meanObservationsPerId": dense["trackContinuityProxies"]["meanDetectionsPerTrackId"],
            "longestContinuousFrames": dense["trackContinuityProxies"]["longestConsecutiveSampledFrames"],
        },
        "horseIdentitySwitchRate": None,
        "horseIdentityAccuracy": None,
        "improvedHorseIdentityProven": False,
        "improvedJraNarPredictionProven": False,
        "notes": "Observation continuity on open-license harness footage only; no annotated truth IDs or horse-specific labels.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--dense", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    dense = json.loads(args.dense.read_text(encoding="utf-8"))
    result = compare(baseline, dense)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                      sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
