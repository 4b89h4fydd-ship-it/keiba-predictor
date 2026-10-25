"""Permissively licensed offline RT-DETR horse detector and ByteTrack tracker.

Model: PekingU/rtdetr_r50vd (Apache-2.0; fixed local HF snapshot).
Tracker: supervision.ByteTrack (MIT).
This adapter intentionally preserves the pre-existing model.track(...) interface
used by the ARVEXQ video pipeline. Track IDs are *not* horse numbers; they are
ephemeral camera-segment identities, to be matched via reviewed information or
provisional OCR consensus. No web requests occur from this module.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

COCO_HORSE_CLASS = 17
DETECTOR_VERSION = "arvexq-apache-rtdetr-mit-bytetrack-v1"


class _AsCpuList:
    """Provide the small tensor interface expected by the old track reader."""
    def __init__(self, items):
        self.items = list(items)

    def cpu(self):
        return self

    def tolist(self):
        return self.items


class _Boxes:
    def __init__(self, ids, boxes, scores, classes):
        self.id = _AsCpuList(ids)
        self.xyxy = _AsCpuList(boxes)
        self.conf = _AsCpuList(scores)
        self.cls = _AsCpuList(classes)


class _Result:
    def __init__(self, ids, boxes, scores, classes):
        self.boxes = _Boxes(ids, boxes, scores, classes)


@lru_cache(maxsize=2)
def _load_local_model(model_dir: str):
    """Load model and processor from a local Apache-2.0 snapshot, offline."""
    try:
        import torch
        from transformers import RTDetrForObjectDetection, RTDetrImageProcessor
    except ImportError as exc:
        raise RuntimeError("Install requirements-vision.txt for RT-DETR inference") from exc
    path = Path(model_dir)
    required = ("config.json", "preprocessor_config.json", "model.safetensors")
    if not path.is_dir() or any(not (path / p).is_file() for p in required):
        raise ValueError("local RT-DETR config/processor/safetensors are required")
    processor = RTDetrImageProcessor.from_pretrained(str(path), local_files_only=True)
    model = RTDetrForObjectDetection.from_pretrained(
        str(path), local_files_only=True, use_safetensors=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device).eval()
    return processor, model, device


class RTDetrByteTracker:
    """Apache RT-DETR + MIT ByteTrack; new instance resets all tracking IDs.

    Loading weights is cached once per process, but camera-cut tracker states
    are *not* cached and never cross camera boundaries.
    """

    def __init__(self, model_dir: str | Path):
        path = Path(model_dir)
        if not path.is_dir():
            raise ValueError("model must be local RT-DETR snapshot directory")
        self.path = str(path)
        self.fps = 30
        self._tracker = None

    def set_frame_rate(self, fps: float):
        if not 0 < float(fps) <= 240:
            raise ValueError("invalid tracker frame rate")
        self.fps = max(1, round(float(fps)))
        self._tracker = None

    def track(self, image: Any, *, persist=True, classes=None, tracker=None,
              conf=0.25, verbose=False):
        """Return one Ultralytics-compatible *data shape*, without Ultralytics."""
        if classes != [COCO_HORSE_CLASS] or tracker != "bytetrack-mit":
            raise ValueError("only open-model COCO horse tracking is supported")
        try:
            import numpy as np
            import supervision as sv
            import torch
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("vision dependencies absent") from exc
        processor, model, device = _load_local_model(self.path)
        # cv2.VideoCapture emits BGR; Hugging Face image processor expects RGB.
        if image is None or not hasattr(image, "shape") or len(image.shape) != 3:
            raise ValueError("decoded RGB/BGR frame required")
        height, width = image.shape[:2]
        rgb = Image.fromarray(image[:, :, ::-1].copy())
        tensors = processor(images=rgb, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**tensors)
        result = processor.post_process_object_detection(
            outputs, threshold=max(0.25, float(conf)), target_sizes=[(height, width)])[0]
        coords, confidences = [], []
        for box, score, label in zip(result["boxes"], result["scores"], result["labels"]):
            if int(label.item()) != COCO_HORSE_CLASS:
                continue
            bounds = [float(v) for v in box.tolist()]
            if len(bounds) == 4 and bounds[2] > bounds[0] and bounds[3] > bounds[1]:
                coords.append(bounds)
                confidences.append(float(score.item()))
        if self._tracker is None:
            self._tracker = sv.ByteTrack(frame_rate=self.fps)
        if coords:
            detections = sv.Detections(
                xyxy=np.asarray(coords, dtype=np.float32).reshape(-1, 4),
                confidence=np.asarray(confidences, dtype=np.float32),
                class_id=np.full(len(coords), COCO_HORSE_CLASS, dtype=np.int32),
            )
        else:
            detections = sv.Detections.empty()
        tracked = self._tracker.update_with_detections(detections)
        if len(tracked) == 0 or tracked.tracker_id is None:
            return [_Result([], [], [], [])]
        return [_Result(
            [int(v) for v in tracked.tracker_id.tolist()],
            tracked.xyxy.tolist(),
            tracked.confidence.tolist() if tracked.confidence is not None
            else [1.0] * len(tracked),
            tracked.class_id.tolist() if tracked.class_id is not None
            else [COCO_HORSE_CLASS] * len(tracked),
        )]
