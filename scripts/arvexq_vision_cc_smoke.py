#!/usr/bin/env python3
"""Live horse-object detector smoke on an attributable CC BY-SA race video.

Not a Japanese JRA/NAR race; it is a video-decoding/detector test ONLY.
Actual stable horse identities, georeferenced metres, forecast hit rates and
betting returns cannot be inferred from this 2015 harness-racing footage.

Video: Horse race in Vienna.webm, Amada44, CC BY-SA 3.0,
https://commons.wikimedia.org/wiki/File:Horse_race_in_Vienna.webm
https://creativecommons.org/licenses/by-sa/3.0/
The downloaded media is never committed, uploaded or redistributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import tempfile
import urllib.request
import sys

# Standalone Github Actions entrypoint; do not require an editable pip install.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/transcoded/7/70/"
    "Horse_race_in_Vienna.webm/Horse_race_in_Vienna.webm.480p.vp9.webm"
)
SOURCE_PAGE = "https://commons.wikimedia.org/wiki/File:Horse_race_in_Vienna.webm"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/3.0/"
ATTRIBUTION = "Amada44, Horse race in Vienna (2015), CC BY-SA 3.0"
MAX_BYTES = 12_000_000
VERSION = "arvexq-live-licensed-horse-video-smoke-v1"


def download_cc_sample(destination: Path, *, opener=None) -> str:
    """Bounded fetch of one explicitly cited CC-licensed Wikimedia transcode."""
    if opener is None:
        opener = urllib.request.urlopen
    req = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "ARVEXQ-OpenCV-Research/1.0 (Wikimedia CC credit)"})
    digest = hashlib.sha256()
    total = 0
    with opener(req, timeout=60) as stream, destination.open("wb") as target:
        response_url = stream.geturl() if hasattr(stream, "geturl") else SOURCE_URL
        if response_url.split("?", 1)[0] != SOURCE_URL:
            raise ValueError("unexpected video redirect")
        while True:
            chunk = stream.read(512 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("CC sample exceeds 12 MB limit")
            digest.update(chunk)
            target.write(chunk)
    if total < 10_000:
        raise ValueError("no usable video bytes returned by Wikimedia")
    return digest.hexdigest()


def run_smoke(video: Path, model_dir: Path, *, max_frames: int = 12,
              sample_hz: float = 1.0,
              capture_factory=None, model_factory=None) -> dict:
    if not (0 < sample_hz <= 30) or not (1 <= max_frames <= 300):
        raise ValueError("bounded sample rate and count required")
    if capture_factory is None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV dependencies are missing") from exc
        capture_factory = cv2.VideoCapture
    if model_factory is None:
        from arvexq.vision.open_detector import RTDetrByteTracker
        model_factory = RTDetrByteTracker
    cap = capture_factory(str(video))
    try:
        if not cap.isOpened():
            raise ValueError("actual CC race video did not decode")
        # cv2 constants: CAP_PROP_FPS=5, CAP_PROP_POS_FRAMES=1
        fps = float(cap.get(5))
        if fps <= 0:
            raise ValueError("invalid sample frame rate")
        model = model_factory(str(model_dir))
        if hasattr(model, "set_frame_rate"):
            model.set_frame_rate(sample_hz)
        # Examine distinct decoded sample times at the specified *effective*
        # tracker update rate. At 1 Hz a racehorse often moves too far between
        # frames for association; 4 Hz is an experimental continuity setting.
        # These are proxy metrics, not verified identities or accuracy.
        sampled, detections, identified = [], 0, set()
        by_track = defaultdict(list)
        previous_frame_index = -1
        for i in range(max_frames):
            frame_idx = round((i + 1) * fps / sample_hz)
            if frame_idx <= previous_frame_index:
                continue
            previous_frame_index = frame_idx
            if hasattr(cap, "set"):
                cap.set(1, frame_idx)
            ok, frame = cap.read()
            if not ok:
                break
            result = model.track(
                frame, persist=True, classes=[17],
                tracker="bytetrack-mit", conf=0.25, verbose=False)
            from arvexq.vision.video_detector import _extract_boxes
            boxes = _extract_boxes(result[0] if result else None)
            sampled.append({"seconds": round(frame_idx / fps, 2),
                            "trackedHorseObjects": len(boxes)})
            detections += len(boxes)
            identified.update(int(b[0]) for b in boxes)
            for b in boxes:
                by_track[int(b[0])].append(i)
    finally:
        cap.release()
    # Count consecutive *sampled* frames for a temporary tracker ID.
    # Fragments/switches cannot be certified without labelled horse identity.
    longest_streak = {}
    for tid, indices in by_track.items():
        longest, streak, prior = 0, 0, None
        for index in indices:
            streak = streak + 1 if prior is not None and index == prior + 1 else 1
            longest = max(longest, streak)
            prior = index
        longest_streak[tid] = longest
    return {
        "version": VERSION,
        "sourcePage": SOURCE_PAGE,
        "sourceAttribution": ATTRIBUTION,
        "sourceLicense": LICENSE_URL,
        "sourceVideoSha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "status": ("horse-objects-detected" if detections else "no-horse-tracks-detected"),
        "testedFrames": len(sampled),
        "sampleRateHz": sample_hz,
        "testedDurationSeconds": round(len(sampled) / sample_hz, 3),
        "horseObjectObservations": detections,
        "distinctTemporaryTrackIds": len(identified),
        "trackContinuityProxies": {
            "tracksWithAtLeast3Detections": sum(len(indices) >= 3 for indices in by_track.values()),
            "longestConsecutiveSampledFrames": max(longest_streak.values(), default=0),
            "meanDetectionsPerTrackId": (round(detections / len(identified), 3)
                                         if identified else None),
            "trackLengthsByTemporaryId": {str(k): len(v) for k, v in sorted(by_track.items())},
            "identitySwitchesVerified": False,
        },
        "trackedFrameMeasurements": sampled,
        "horseNumberRecognitionTested": False,
        "horseIdentityAccuracyKnown": False,
        "metresCalibrationTested": False,
        "japaneseRaceForecastAccuracyProved": False,
        "predictionApplied": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path,
                        default=Path(".arvexq-data/vision-model"))
    parser.add_argument("--output", type=Path,
                        default=Path(".arvexq-data/vision-smoke.json"))
    parser.add_argument("--sample-hz", type=float, default=1.0,
                        help="Effective tracker frequency; e.g. 1 or 4 Hz")
    parser.add_argument("--seconds", type=int, default=12,
                        help="Duration from second 1 (bounded <=60 s)")
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= 60 or not 0 < args.sample_hz <= 30:
        parser.error("Invalid seconds or sample-hz")
    samples = round(args.seconds * args.sample_hz)
    if not 1 <= samples <= 300:
        parser.error("Too many sampled frames")
    with tempfile.TemporaryDirectory(prefix="arvexq-public-cc-video-") as folder:
        video = Path(folder) / "licensed-clip.webm"
        download_cc_sample(video)
        result = run_smoke(video, args.model_dir, max_frames=samples,
                           sample_hz=args.sample_hz)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["horseObjectObservations"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
