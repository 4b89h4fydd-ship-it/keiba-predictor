"""Auditable telemetry derived from externally identified horse observations.

This is the *measurement* layer, not a trained computer-vision detector. A
video detector must provide ground-plane, calibrated observations together with
stable horse identities. Invisible horses never receive imputed measurements.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from math import hypot, isfinite
from typing import Any

VERSION = "arvexq-vision-observations-v1"


def _finite(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a measurement")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("non-numeric measurement") from exc
    if not isfinite(result):
        raise ValueError("non-finite measurement")
    return result


def analyze_tracking(manifest: dict[str, Any], horse_numbers: list[int]) -> dict[str, Any]:
    """Summarize verified tracking positions without inventing hidden motion.

    Observations are measurements from a separate video-detection stage. The
    source hash binds the output to the video; ground-plane calibration must
    have been verified by that stage before distances are called metres.
    """
    if not isinstance(manifest, dict):
        raise ValueError("tracking manifest required")
    source = manifest.get("source") or {}
    digest = str(source.get("sha256") or "").lower()
    if (source.get("rightsVerified") is not True
            or source.get("calibrationVerified") is not True
            or source.get("coordinateSystem") != "ground-plane-meters"
            or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
        raise ValueError("authorized calibrated video provenance is required")
    if not manifest.get("raceId") or not manifest.get("raceDate"):
        raise ValueError("race identity required")
    if not isinstance(horse_numbers, list) or len(horse_numbers) < 2:
        raise ValueError("complete runner roster required")
    if any(type(n) is not int or n <= 0 for n in horse_numbers) or len(set(horse_numbers)) != len(horse_numbers):
        raise ValueError("invalid runner identities")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or len(frames) < 2:
        raise ValueError("multiple timed frames required")
    valid = set(horse_numbers)
    seen: dict[int, list[tuple[float, float, float, str]]] = defaultdict(list)
    previous_time = None
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("invalid frame")
        t = _finite(frame.get("timeSeconds"))
        if t < 0 or (previous_time is not None and t <= previous_time):
            raise ValueError("frames must be in strictly increasing time order")
        previous_time = t
        camera = str(frame.get("cameraId") or "")
        if not camera:
            raise ValueError("camera identity is required for cut detection")
        observed = set()
        detections = frame.get("horses") or []
        if not isinstance(detections, list):
            raise ValueError("invalid detections")
        for detection in detections:
            if not isinstance(detection, dict):
                raise ValueError("invalid horse detection")
            no = detection.get("horseNumber")
            if type(no) is not int or no not in valid or no in observed:
                raise ValueError("unknown or duplicate horse detection")
            observed.add(no)
            conf = _finite(detection.get("identityConfidence"))
            if not 0 <= conf <= 1:
                raise ValueError("invalid identity confidence")
            if conf < 0.8 or detection.get("visible") is not True:
                continue
            x = _finite(detection.get("xMeters"))
            y = _finite(detection.get("yMeters"))
            seen[no].append((t, x, y, camera))
    results = []
    max_gap_seconds = 1.5
    max_plausible_speed = 25.0
    for no in sorted(valid):
        observations = seen[no]
        observed_path = 0.0
        speed_samples: list[tuple[float, float]] = []
        accepted_segments = 0
        # No interpolation across unobserved footage, cuts, or implausible jumps.
        for prev, curr in zip(observations, observations[1:]):
            t, x, y, camera = curr
            dt = t - prev[0]
            if dt <= 0 or dt > max_gap_seconds or camera != prev[3]:
                continue
            distance = hypot(x - prev[1], y - prev[2])
            speed = distance / dt
            if speed > max_plausible_speed:
                continue
            observed_path += distance
            accepted_segments += 1
            speed_samples.append((t, speed))
        slowdowns = []
        for before, after in zip(speed_samples, speed_samples[1:]):
            dt = after[0] - before[0]
            if 0 < dt <= max_gap_seconds and before[1] >= 8.0:
                change_per_second = (after[1] - before[1]) / dt
                if change_per_second <= -4.0:
                    slowdowns.append({"timeSeconds": after[0],
                                      "decelerationMps2": round(change_per_second, 2),
                                      "classification": "possible-deceleration-not-causation"})
        # A full-race path-loss estimate requires matched segment reference
        # geometry. Never compare an incomplete observed path to race distance.
        reference = (manifest.get("referencePathMetersByHorse") or {}).get(str(no))
        measured_loss = None
        if (reference is not None and accepted_segments == len(frames) - 1
                and len(observations) == len(frames)):
            reference_meters = _finite(reference)
            if reference_meters <= 0:
                raise ValueError("reference path must be positive")
            measured_loss = round(max(0.0, observed_path - reference_meters), 2)
        results.append({
            "horseNumber": no,
            "observedFrames": len(observations),
            "totalFrames": len(frames),
            "coverage": round(len(observations) / len(frames), 4),
            "validMovementSegments": accepted_segments,
            "observedPathMeters": round(observed_path, 2) if accepted_segments else None,
            "averageObservedSpeedMps": (round(sum(speed for _, speed in speed_samples) / len(speed_samples), 3)
                                        if speed_samples else None),
            "possibleSlowdowns": slowdowns,
            "distanceLossMeters": measured_loss,
            "interference": "not-determined-from-tracks-alone",
            "observationStatus": "observed" if accepted_segments else "insufficient-tracking",
        })
    evidence_hash = sha256(repr((digest, manifest["raceId"], manifest["raceDate"], results)).encode()).hexdigest()
    return {
        "version": VERSION,
        "raceId": str(manifest["raceId"]), "raceDate": str(manifest["raceDate"]),
        "videoSha256": digest, "evidenceHash": evidence_hash,
        "analysisStatus": "tracking-measurements-not-a-validated-video-model",
        "runners": results,
    }
