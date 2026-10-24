"""Conservative automatic saddlecloth/horse-number assignment from video frames.

YOLO/ByteTrack IDs are temporary tracklets, not real horse numbers. OCR reads
are accepted only when several independent visible frames agree, classifiable
as a single horse number from the *actual entry list*. Every claim retains its
automated provenance; accuracy must be independently measured before it can
become a production prediction feature.
"""
from __future__ import annotations

from collections import defaultdict
from math import isfinite
from typing import Any

VERSION = "arvexq-auto-saddlecloth-v1"


def read_saddlecloth_number(image: Any, xyxy: tuple[float, float, float, float]) -> dict | None:
    """Optional Tesseract OCR on a cropped body region; returns UNVERIFIED read.

    This heuristic is explicitly not a validated saddlecloth recognizer.
    Caller aggregates repeated independent reads and refuses ambiguity.
    """
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("pytesseract is required for automatic identity reads") from exc
    x1, y1, x2, y2 = map(int, xyxy)
    if x2 - x1 < 15 or y2 - y1 < 15:
        return None
    # Crop to a plausible saddlecloth area; horse direction varies and a
    # race-specific trained saddlecloth detector would improve this.
    h, w = image.shape[:2]
    left = max(0, min(w, x1 + (x2 - x1) // 4))
    right = max(0, min(w, x1 + 3 * (x2 - x1) // 4))
    top = max(0, min(h, y1 + (y2 - y1) // 3))
    bottom = max(0, min(h, y1 + 4 * (y2 - y1) // 5))
    patch = image[top:bottom, left:right]
    if getattr(patch, "size", 0) == 0:
        return None
    data = pytesseract.image_to_data(
        patch, output_type=pytesseract.Output.DICT,
        config="--psm 11 -c tessedit_char_whitelist=0123456789")
    candidates = []
    for value, raw_score in zip(data.get("text", []), data.get("conf", [])):
        value = str(value).strip()
        if not value.isdigit():
            continue
        number = int(value)
        try:
            score = float(raw_score) / 100.0
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 99 and isfinite(score) and score >= 0.92:
            candidates.append((number, score))
    if len(candidates) != 1:
        return None
    no, conf = candidates[0]
    return {"horseNumber": no, "confidence": conf, "source": "automated-ocr"}


def resolve_ocr_identities(
    reads: list[dict[str, Any]],
    horse_numbers: list[int],
    *,
    min_independent_frames: int = 3,
    min_vote_share: float = 0.85,
    min_read_confidence: float = 0.92,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Tracklet -> horseNumber assignments with one-to-one uniqueness per camera.

    Counts *all observed candidate frames* as the denominator, including low
    quality and empty OCR reads. A single lucky OCR read cannot assign a horse.
    Any multiple-track claimant of the same horse in one camera is rejected.
    """
    roster = set(horse_numbers)
    if not roster or len(roster) != len(horse_numbers):
        raise ValueError("valid full roster required")
    if min_independent_frames < 3 or not 0.5 < min_vote_share <= 1:
        raise ValueError("unsafe OCR aggregation thresholds")
    frames_by_track = defaultdict(dict)
    for row in reads:
        if not isinstance(row, dict):
            raise ValueError("invalid OCR observation")
        camera, track = str(row.get("cameraId") or ""), row.get("trackId")
        if not camera.startswith("camera-") or type(track) is not int:
            raise ValueError("camera and tracker identity required")
        time = row.get("timeSeconds")
        if isinstance(time, bool) or not isinstance(time, (int, float)) or not isfinite(time):
            raise ValueError("frame time required")
        key = (camera, track)
        if time in frames_by_track[key]:
            raise ValueError("duplicate OCR read in same tracker frame")
        frame = {"horseNumber": None, "confidence": 0.0}
        no, conf = row.get("horseNumber"), row.get("confidence")
        if type(no) is int and no in roster and type(conf) in (int, float) and isfinite(conf) and conf >= min_read_confidence:
            frame = {"horseNumber": no, "confidence": float(conf)}
        frames_by_track[key][time] = frame

    provisional = {}
    for (camera, track), samples in frames_by_track.items():
        if len(samples) < min_independent_frames:
            continue
        counts = defaultdict(int)
        confidence = defaultdict(list)
        for sample in samples.values():
            no = sample["horseNumber"]
            if no is not None:
                counts[no] += 1
                confidence[no].append(sample["confidence"])
        if not counts:
            continue
        best = sorted(counts, key=lambda no: (-counts[no], no))[0]
        votes = counts[best]
        if votes < min_independent_frames or votes / len(samples) < min_vote_share:
            continue
        provisional[(camera, track)] = {
            "horseNumber": best,
            "evidence": "automated-saddlecloth-ocr-consensus",
            "verified": False,
            "identityConfidence": round(sum(confidence[best]) / len(confidence[best]), 4),
            "independentFrames": votes,
            "observedFrames": len(samples),
            "voteShare": round(votes / len(samples), 4),
        }
    claimants = defaultdict(list)
    for (camera, track), value in provisional.items():
        claimants[(camera, value["horseNumber"])].append(track)
    return {
        camera: {
            str(track): value for (cam, track), value in provisional.items()
            if cam == camera and len(claimants[(cam, value["horseNumber"])]) == 1
        }
        for camera, _ in provisional
    }
