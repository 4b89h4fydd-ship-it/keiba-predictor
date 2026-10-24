#!/usr/bin/env python3
"""Offline ARVEXQ video analysis; authorized local video only.

Usage:
  python scripts/arvexq_video_analyze.py --video race.mp4 \
    --config race-video.json --weights horse-detector.pt \
    --output race-evidence.json

Config must include raceId, raceDate, rightsVerified=true, the complete
horseNumbers roster, reviewed ground-plane homography and reviewedIdentityMap.
Unknown track IDs are NEVER assigned a horseNumber automatically.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.vision.video_detector import collect_video


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline visual horse tracking")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = collect_video(args.video, config, model_path=args.weights)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    measurements = report["measurements"]
    print(json.dumps({
        "status": "measured-not-trained-or-validated",
        "raceId": measurements["raceId"],
        "videoSha256": measurements["videoSha256"],
        "runnersWithObservedMotion": sum(
            bool(row["validMovementSegments"]) for row in measurements["runners"]),
        "totalRunners": len(measurements["runners"]),
        "unidentifiedDetections": report["manifest"]["capture"]["unidentifiedDetections"],
        "forecastUpdated": False,
        "output": str(args.output),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
