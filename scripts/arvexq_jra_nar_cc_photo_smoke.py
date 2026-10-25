#!/usr/bin/env python3
"""Check the Apache RT-DETR horse model against actual JRA/NAR race PHOTOGRAPHS.

These are independently CC-licensed photographer uploads at Wikimedia Commons,
NOT JRA/NAR race video or race-broadcast frames. It is a distribution-shift
detector smoke, not per-horse recognition, motion tracking or betting validation.

The original images are ephemeral in memory and never committed/artifacted.
Our generated JSON preserves attribution, Commons source, license and SHA256.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = "arvexq-jra-nar-cc-still-detection-v1"
MAX_FILE_BYTES = 12_000_000
LICENSE_CC_BY_SA_3 = "https://creativecommons.org/licenses/by-sa/3.0/"
LICENSE_CC_BY_SA_4 = "https://creativecommons.org/licenses/by-sa/4.0/"
SAMPLES = (
    {
        "circuit": "JRA",
        "description": "2019 Tokyo Yushun finishing horses, photographer-owned photo",
        "file": "Roger Barows Tokyo Yushun 2019(IMG2).jpg",
        "author": "Nadaraikon",
        "license": LICENSE_CC_BY_SA_3,
        "source": "https://commons.wikimedia.org/wiki/File:Roger_Barows_Tokyo_Yushun_2019(IMG2).jpg",
    },
    {
        "circuit": "NAR",
        "description": "2020 Sonoda Racecourse finish, photographer-owned photo",
        "file": "Jingi and Centurion 201001.jpg",
        "author": "Fusianasan1350",
        "license": LICENSE_CC_BY_SA_4,
        "source": "https://commons.wikimedia.org/wiki/File:Jingi_and_Centurion_201001.jpg",
    },
)


def download_cc_photo(sample: dict, *, opener=None) -> bytes:
    if opener is None:
        opener = urlopen
    if not isinstance(sample, dict) or sample not in SAMPLES:
        raise ValueError("Only individually sourced and CC-attributed samples permitted")
    file_name = sample["file"]
    url = ("https://commons.wikimedia.org/wiki/Special:Redirect/file/"
           + quote(file_name, safe=""))
    req = Request(url, headers={"User-Agent": "ARVEXQ-Noncommercial-Test-HorsePhotos/1.0"})
    with opener(req, timeout=45) as response:
        if hasattr(response, "geturl"):
            final = urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname not in (
                "upload.wikimedia.org", "commons.wikimedia.org"):
                raise ValueError("photo download redirected outside Wikimedia")
        payload = response.read(MAX_FILE_BYTES + 1)
    if len(payload) < 2_000 or len(payload) > MAX_FILE_BYTES:
        raise ValueError("photo missing, invalid or exceeds size cap")
    return payload


def infer_horses(image_bytes: bytes, model_dir: Path) -> dict:
    try:
        import torch
        from PIL import Image, ImageOps
        from arvexq.vision.open_detector import COCO_HORSE_CLASS, _load_local_model
    except ImportError as exc:
        raise RuntimeError("Install requirements-vision.txt") from exc

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    width, height = image.size
    if width < 50 or height < 50 or width * height > 50_000_000:
        raise ValueError("photo dimensions outside bounded inference limits")
    # Original model was validated for full-frame horse boxes. Do not claim
    # identity/number recognition from an individual still photograph.
    processor, model, device = _load_local_model(str(model_dir))
    tensors = processor(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**tensors)
    decoded = processor.post_process_object_detection(
        outputs, threshold=0.25, target_sizes=[(height, width)])[0]
    horse_scores = [
        float(score.item())
        for score, label in zip(decoded["scores"], decoded["labels"])
        if int(label.item()) == COCO_HORSE_CLASS
    ]
    return {
        "width": width, "height": height,
        "detectedHorseObjects": len(horse_scores),
        "maxDetectionConfidence": round(max(horse_scores), 5)
        if horse_scores else None,
        "isHumanValidated": False,
    }


def evaluate(model_dir: Path, *, downloader=None, inferrer=None) -> dict:
    downloader = downloader or download_cc_photo
    inferrer = inferrer or infer_horses
    results = []
    for sample in SAMPLES:
        content = downloader(sample)
        measurements = inferrer(content, model_dir)
        if not isinstance(measurements, dict):
            raise ValueError("detector result unavailable")
        horses = measurements.get("detectedHorseObjects")
        if type(horses) is not int or horses < 0:
            raise ValueError("missing actual detection count")
        results.append({
            "circuit": sample["circuit"], "photoDescription": sample["description"],
            "source": sample["source"], "credit": sample["author"],
            "license": sample["license"], "sourceSha256": sha256(content).hexdigest(),
            **measurements,
            "horseNumberAccuracy": None,
            "groundTruthHorseCount": None,
            "reidentificationTested": False,
            "horseMotionOrPaceTested": False,
            "modelImprovesBettingProven": False,
        })
    return {
        "version": VERSION,
        "cases": results,
        "circuitCoverage": ["JRA", "NAR"],
        "mediaType": "still-photographs-not-videos",
        "independentlyReviewedDetections": False,
        "forecastUpdated": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path,
                        default=Path(".arvexq-data/vision-model"))
    parser.add_argument("--output", type=Path,
                        default=Path(".arvexq-data/jra-nar-photo-detector.json"))
    args = parser.parse_args(argv)
    result = evaluate(args.model_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    # The test genuinely runs, but zero detections are a diagnostic result,
    # not an inferred "success". The no-horse count is retained for audit.
    return 0 if all(r["detectedHorseObjects"] > 0 for r in result["cases"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
