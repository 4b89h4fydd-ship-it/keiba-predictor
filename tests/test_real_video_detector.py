"""Mocked-video detector contract tests; no model downloads or private media."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from arvexq.vision.video_detector import (
    COCO_HORSE_CLASS, collect_video, project_ground, _extract_boxes,
)


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class FakeBoxes:
    def __init__(self, detections):
        self.id = FakeTensor([x[0] for x in detections])
        self.xyxy = FakeTensor([x[1] for x in detections])
        self.conf = FakeTensor([x[2] for x in detections])
        self.cls = FakeTensor([x[3] for x in detections])


class FakeResult:
    def __init__(self, detections):
        self.boxes = FakeBoxes(detections)


class FakeCapture:
    def __init__(self, frames=3):
        self.frames = frames
        self.index = 0
        self.released = False

    def isOpened(self):
        return True

    def get(self, prop):
        assert prop == 5
        return 1.0

    def read(self):
        if self.index >= self.frames:
            return False, None
        value = self.index
        self.index += 1
        return True, value

    def release(self):
        self.released = True


class FakeModel:
    def __init__(self, filename):
        self.filename = filename

    def track(self, image, **kwargs):
        assert kwargs["classes"] == [COCO_HORSE_CLASS]
        assert kwargs["tracker"] == "bytetrack-mit"
        x = float(image * 5)
        return [FakeResult([
            (7, [x - .5, 0.0, x + .5, 1.0], .99, 17),
            (8, [x - .5, 1.0, x + .5, 2.0], .91, 17),
            (9, [x - .5, 2.0, x + .5, 3.0], .99, 16),  # dog, excluded
        ])]


def config():
    return {
        "raceId": "nar-2026-10-25-園田-01",
        "raceDate": "2026-10-25",
        "rightsVerified": True,
        "horseNumbers": [1, 2],
        "calibration": {
            "reviewed": True,
            "coordinateSystem": "ground-plane-meters",
            "source": "surveyed track control points and external human review",
            "homography": [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
        },
        "verifiedIdentityMap": {
            "camera-0": {
                "7": {"horseNumber": 1, "verified": True,
                      "evidence": "reviewed saddlecloth frame 1"},
                "8": {"horseNumber": 2, "verified": True,
                      "evidence": "reviewed saddlecloth frame 1"},
            }
        },
        "referencePathMetersByHorse": {"1": 9.},
        "cameraCutsSeconds": [],
    }


class VideoDetectorTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.video = folder / "video.mp4"
        self.weights = folder / "weights.pt"
        self.video.write_bytes(b"fake local video for mocked decoding")
        self.weights.write_bytes(b"fake model for test factory")
        self.capture = FakeCapture()

    def tearDown(self):
        self.tmp.cleanup()

    def collect(self, configuration):
        return collect_video(self.video, configuration, model_path=self.weights,
                             capture_factory=lambda path: self.capture,
                             model_factory=FakeModel)

    def test_detects_horses_and_calculates_ground_plane_path(self):
        report = self.collect(config())
        self.assertEqual(report["version"], "arvexq-video-detector-v1")
        self.assertEqual(report["manifest"]["capture"]["unidentifiedDetections"], 0)
        self.assertEqual(report["manifest"]["model"]["horseClassId"], 17)
        self.assertEqual(report["measurements"]["runners"][0]["coverage"], 1.)
        self.assertEqual(report["measurements"]["runners"][0]["observedPathMeters"], 10.)
        self.assertEqual(report["measurements"]["runners"][0]["distanceLossMeters"], 1.)
        self.assertFalse(report["predictionApplied"])
        self.assertTrue(self.capture.released)

    def test_unknown_trackers_are_not_guessed_as_real_horses(self):
        cfg = config()
        cfg["verifiedIdentityMap"] = {}
        report = self.collect(cfg)
        self.assertEqual(report["manifest"]["capture"]["unidentifiedDetections"], 6)
        self.assertEqual(report["measurements"]["runners"][0]["coverage"], 0)
        self.assertIsNone(report["measurements"]["runners"][0]["distanceLossMeters"])

    def test_camera_cut_resets_tracker_and_breaks_path(self):
        cfg = config()
        cfg["cameraCutsSeconds"] = [2.]
        cfg["calibration"]["homographies"] = {
            "camera-0": deepcopy(cfg["calibration"]["homography"]),
            "camera-1": deepcopy(cfg["calibration"]["homography"]),
        }
        cfg["verifiedIdentityMap"]["camera-1"] = deepcopy(
            cfg["verifiedIdentityMap"]["camera-0"])
        count = []

        def factory(filename):
            count.append(filename)
            return FakeModel(filename)

        report = collect_video(self.video, cfg, model_path=self.weights,
                               capture_factory=lambda path: self.capture,
                               model_factory=factory)
        self.assertEqual(len(count), 2)
        self.assertEqual(report["manifest"]["frames"][-1]["cameraId"], "camera-1")
        self.assertEqual(report["measurements"]["runners"][0]["observedPathMeters"], 5.)
        self.assertIsNone(report["measurements"]["runners"][0]["distanceLossMeters"])

    def test_camera_changes_without_calibration_cannot_measure_metres(self):
        cfg = config()
        cfg["cameraCutsSeconds"] = [2.]
        with self.assertRaisesRegex(ValueError, "each camera segment"):
            self.collect(cfg)
        cfg["calibration"]["homographies"] = {
            "camera-0": deepcopy(cfg["calibration"]["homography"])}
        with self.assertRaisesRegex(ValueError, "every camera segment"):
            self.collect(cfg)

    def test_identity_must_be_reviewed_and_unique(self):
        cfg = config()
        cfg["verifiedIdentityMap"]["camera-0"]["7"]["verified"] = False
        with self.assertRaisesRegex(ValueError, "reviewed horse identity"):
            self.collect(cfg)
        cfg = config()
        cfg["verifiedIdentityMap"]["camera-0"]["8"]["horseNumber"] = 1
        with self.assertRaisesRegex(ValueError, "same horse"):
            self.collect(cfg)

    def test_rejects_unlicensed_media_and_unreviewed_calibration(self):
        cfg = config()
        cfg["rightsVerified"] = False
        with self.assertRaisesRegex(ValueError, "rights"):
            self.collect(cfg)
        cfg = config()
        cfg["calibration"]["reviewed"] = False
        with self.assertRaisesRegex(ValueError, "calibration"):
            self.collect(cfg)

    def test_math_and_empty_tracking_guard(self):
        self.assertEqual(project_ground(4, 3, [[2,0,0],[0,2,0],[0,0,1]]),
                         (8, 6))
        with self.assertRaisesRegex(ValueError, "infinity"):
            project_ground(1, 1, [[1,0,0],[0,1,0],[0,0,0]])
        class NoIdBoxes:
            id = None
        class NoIdResult:
            boxes = NoIdBoxes()
        self.assertEqual(_extract_boxes(NoIdResult()), [])
