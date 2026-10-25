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
              capture_factory=None, model_factory=None) -> dict:
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
            model.set_frame_rate(1.0)
        # Start after first second and inspect a consecutive one-Hz window.
        # Detector accuracy requires independent frame-level truth labels.
        sampled, detections, identified = [], 0, set()
        for i in range(max_frames):
            frame_idx = round((i + 1) * fps)
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
    finally:
        cap.release()
    return {
        "version": VERSION,
        "sourcePage": SOURCE_PAGE,
        "sourceAttribution": ATTRIBUTION,
        "sourceLicense": LICENSE_URL,
        "sourceVideoSha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "status": ("horse-objects-detected" if detections else "no-horse-tracks-detected"),
        "testedFrames": len(sampled),
        "horseObjectObservations": detections,
        "distinctTemporaryTrackIds": len(identified),
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
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="arvexq-public-cc-video-") as folder:
        video = Path(folder) / "licensed-clip.webm"
        download_cc_sample(video)
        result = run_smoke(video, args.model_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["horseObjectObservations"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
