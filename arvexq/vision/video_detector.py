"""Video horse detection/tracking -> provenance-checked ARVEXQ measurements.

YOLO detects COCO-class horses and ByteTrack assigns temporary tracker IDs.
A temporary tracker ID is NEVER assumed to be an entry/horse number. An
independently reviewed segment-specific identity map is required before the
detection is admitted as horse-level evidence. Homography must be reviewed
against surveyed reference points before any coordinate is called metres.

GPU/Python ML dependencies are optional and imported only at execution time.
No race video is downloaded and this module does not change forecast marks.
"""
from __future__ import annotations

import hashlib
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any, Callable

from arvexq.vision.observations import analyze_tracking

VERSION = "arvexq-video-detector-v1"
COCO_HORSE_CLASS = 17


def _number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid numeric value") from exc
    if not isfinite(result):
        raise ValueError("non-finite numeric value")
    return result


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def project_ground(x: float, y: float, matrix: list[list[float]]) -> tuple[float, float]:
    """Project bottom-centre horse location to ground-plane metres."""
    if not isinstance(matrix, list) or len(matrix) != 3:
        raise ValueError("3x3 ground-plane homography required")
    if any(not isinstance(row, list) or len(row) != 3 for row in matrix):
        raise ValueError("3x3 ground-plane homography required")
    a = [[_number(cell) for cell in row] for row in matrix]
    x, y = _number(x), _number(y)
    denominator = a[2][0] * x + a[2][1] * y + a[2][2]
    if abs(denominator) < 1e-10:
        raise ValueError("projection maps to infinity")
    return ((a[0][0] * x + a[0][1] * y + a[0][2]) / denominator,
            (a[1][0] * x + a[1][1] * y + a[1][2]) / denominator)


def _validated_config(config: dict[str, Any]) -> tuple[list[int], list[float], dict]:
    if not isinstance(config, dict):
        raise ValueError("race configuration required")
    try:
        date.fromisoformat(config["raceDate"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("valid race date required") from exc
    if not str(config.get("raceId") or "").strip():
        raise ValueError("race identity required")
    if config.get("rightsVerified") is not True:
        raise ValueError("source video rights must be verified before processing")
    roster = config.get("horseNumbers")
    if (not isinstance(roster, list) or len(roster) < 2
            or any(type(n) is not int or n <= 0 for n in roster)
            or len(set(roster)) != len(roster)):
        raise ValueError("unique complete horse roster required")
    calibration = config.get("calibration") or {}
    if (calibration.get("reviewed") is not True
            or calibration.get("coordinateSystem") != "ground-plane-meters"
            or not str(calibration.get("source") or "").strip()):
        raise ValueError("independently reviewed surveyed calibration required")
    raw_cuts = config.get("cameraCutsSeconds") or []
    if not isinstance(raw_cuts, list):
        raise ValueError("camera cuts must be a list")
    cuts = [_number(t) for t in raw_cuts]
    if any(t <= 0 for t in cuts) or cuts != sorted(set(cuts)):
        raise ValueError("camera cuts must be sorted unique positive times")
    transforms = calibration.get("homographies")
    if cuts or transforms is not None:
        if not isinstance(transforms, dict):
            raise ValueError("each camera segment requires its own reviewed homography")
        required = {f"camera-{i}" for i in range(len(cuts) + 1)}
        if set(transforms) != required:
            raise ValueError("reviewed homography required for every camera segment")
        for matrix in transforms.values():
            project_ground(0, 0, matrix)
    else:
        project_ground(0, 0, calibration.get("homography"))
    identity_map = config.get("verifiedIdentityMap") or {}
    if not isinstance(identity_map, dict):
        raise ValueError("reviewed segment identities must be a mapping")
    for camera, tracks in identity_map.items():
        if not isinstance(camera, str) or not camera.startswith("camera-") or not isinstance(tracks, dict):
            raise ValueError("identity maps must be camera-specific")
        numbers = []
        for tracker_id, record in tracks.items():
            try:
                int(tracker_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid tracker identity") from exc
            if (not isinstance(record, dict) or record.get("verified") is not True
                    or type(record.get("horseNumber")) is not int
                    or record["horseNumber"] not in roster
                    or not str(record.get("evidence") or "").strip()):
                raise ValueError("reviewed horse identity with evidence is required")
            numbers.append(record["horseNumber"])
        if len(numbers) != len(set(numbers)):
            raise ValueError("different trackers cannot map to the same horse in one segment")
    return roster, cuts, identity_map


def _extract_boxes(result: Any) -> list[tuple[int, float, float, float]]:
    """Extract actual model track IDs, detection scores and ground-contact pixels."""
    if result is None:
        return []
    boxes = getattr(result, "boxes", None)
    if boxes is None or getattr(boxes, "id", None) is None:
        return []
    ids = boxes.id.cpu().tolist()
    xyxy = boxes.xyxy.cpu().tolist()
    confidence = boxes.conf.cpu().tolist()
    classes = boxes.cls.cpu().tolist()
    output = []
    for track_id, bounds, score, cls in zip(ids, xyxy, confidence, classes):
        if int(cls) != COCO_HORSE_CLASS:
            continue
        if len(bounds) != 4 or float(score) < 0.25:
            continue
        x1, y1, x2, y2 = map(_number, bounds)
        if x2 <= x1 or y2 <= y1:
            continue
        output.append((int(track_id), _number(score), (x1 + x2) / 2, y2))
    return output


def collect_video(video_path: str | Path, config: dict[str, Any], *,
                  model_path: str | Path,
                  capture_factory: Callable | None = None,
                  model_factory: Callable | None = None) -> dict[str, Any]:
    """Run a pretrained horse detector on EVERY decoded frame and track IDs.

    Returned unknown tracks are counts only, never falsely named horses.
    A cut resets the tracking model so IDs cannot silently bridge cameras.
    Actual missed horses are not interpolated. Sampling is explicit.
    """
    roster, cuts, identity_map = _validated_config(config)
    path = Path(video_path)
    weights = Path(model_path)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("readable nonempty local video required")
    if not weights.is_file() or not weights.stat().st_size:
        raise ValueError("explicit local model weights required; automatic download disabled")
    if capture_factory is None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV required: install requirements-vision.txt") from exc
        capture_factory = cv2.VideoCapture
    if model_factory is None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Ultralytics required: install requirements-vision.txt") from exc
        model_factory = YOLO
    cap = capture_factory(str(path))
    try:
        if not cap.isOpened():
            raise ValueError("unable to decode video")
        # OpenCV CAP_PROP_FPS = 5; avoid importing cv2 in the pure test adapter.
        fps = _number(cap.get(5))
        if fps <= 0 or fps > 240:
            raise ValueError("valid video frames-per-second metadata required")
        stride = config.get("sampleEveryNFrames", 1)
        if type(stride) is not int or not 1 <= stride <= 120:
            raise ValueError("sampleEveryNFrames must be 1..120")
        frames = []
        frame_index = 0
        cut_index = 0
        unidentified_count = 0
        model = model_factory(str(weights))
        while True:
            success, image = cap.read()
            if not success:
                break
            t = frame_index / fps
            frame_index += 1
            if (frame_index - 1) % stride:
                continue
            while cut_index < len(cuts) and t >= cuts[cut_index]:
                cut_index += 1
                model = model_factory(str(weights))  # track states are camera-specific
            camera = f"camera-{cut_index}"
            inference = model.track(image, persist=True, classes=[COCO_HORSE_CLASS],
                                    tracker="bytetrack.yaml", conf=0.25, verbose=False)
            tracks = _extract_boxes(inference[0] if inference else None)
            detections = []
            seen = set()
            for track_id, score, pixel_x, pixel_y in tracks:
                mapping = identity_map.get(camera, {}).get(str(track_id))
                if mapping is None:
                    unidentified_count += 1
                    continue
                no = mapping["horseNumber"]
                # Multiple detections mapped to the same entry in one frame
                # indicate inconsistent tracking/identity evidence; fail closed.
                if no in seen:
                    raise ValueError("conflicting track mapping for a horse")
                seen.add(no)
                transforms = config["calibration"].get("homographies")
                matrix = (transforms[camera] if transforms is not None
                          else config["calibration"]["homography"])
                ground_x, ground_y = project_ground(pixel_x, pixel_y, matrix)
                detections.append({
                    "horseNumber": no, "xMeters": ground_x, "yMeters": ground_y,
                    "visible": True, "identityConfidence": 1.0,
                    "detectionConfidence": round(score, 5),
                    "trackId": track_id,
                })
            frames.append({"timeSeconds": round(t, 6), "cameraId": camera,
                           "horses": detections})
        if len(frames) < 2:
            raise ValueError("at least two decoded sampled frames required")
    finally:
        cap.release()
    manifest = {
        "raceId": config["raceId"], "raceDate": config["raceDate"],
        "source": {"sha256": _digest(path), "rightsVerified": True,
                   "calibrationVerified": True,
                   "coordinateSystem": "ground-plane-meters"},
        "model": {"weightsSha256": _digest(weights), "detector": "ultralytics-yolo",
                  "horseClassId": COCO_HORSE_CLASS, "tracker": "bytetrack"},
        "frames": frames,
        "referencePathMetersByHorse": config.get("referencePathMetersByHorse") or {},
        "capture": {"originalDecodedFrames": frame_index, "sampledFrames": len(frames),
                    "sampleStride": stride, "fps": fps,
                    "unidentifiedDetections": unidentified_count,
                    "cameraCutsDeclared": len(cuts),
                    "identityMapping": "reviewed-per-camera-track-ids-not-auto-identification"},
    }
    measurements = analyze_tracking(manifest, roster)
    return {"version": VERSION, "manifest": manifest, "measurements": measurements,
            "predictionApplied": False,
            "note": "未検証の映像特徴量は予想の印・買い目へ自動加点しない"}
