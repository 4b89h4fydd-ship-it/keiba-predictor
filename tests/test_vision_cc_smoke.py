"""CC video smoke isolated tests; production CI runs real remote CC media separately."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.arvexq_vision_track_ablation import compare
from scripts.arvexq_vision_cc_smoke import (
    ATTRIBUTION, LICENSE_URL, VERSION, SOURCE_URL,
    download_cc_sample, run_smoke,
)


class FakeStream:
    def __init__(self, data):
        self.data = data
        self.sent = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def geturl(self):
        return SOURCE_URL

    def read(self, n):
        if self.sent:
            return b""
        self.sent = True
        return self.data


class Capture:
    def __init__(self):
        self.frame = 0
        self.released = False

    def isOpened(self):
        return True

    def get(self, p):
        assert p == 5
        return 30

    def set(self, prop, frame):
        assert prop == 1
        self.frame = frame

    def read(self):
        return True, self.frame

    def release(self):
        self.released = True


class FakeTensor:
    def __init__(self, x):
        self.x = x

    def cpu(self):
        return self

    def tolist(self):
        return self.x


class FakeModel:
    def __init__(self, path):
        self.fps = None

    def set_frame_rate(self, fps):
        self.fps = fps

    def track(self, frame, **kwargs):
        assert kwargs["tracker"] == "bytetrack-mit"
        assert kwargs["classes"] == [17]
        class Boxes:
            id = FakeTensor([1])
            xyxy = FakeTensor([[10., 10., 35., 30.]])
            conf = FakeTensor([.97])
            cls = FakeTensor([17])
        class Output:
            boxes = Boxes()
        return [Output()]


class LicensedRaceSmokeTests(TestCase):
    def test_attribution_and_license_explicit(self):
        self.assertIn("Amada44", ATTRIBUTION)
        self.assertIn("by-sa/3.0", LICENSE_URL)
        self.assertIn("480p", SOURCE_URL)

    def test_isolated_video_detection_does_not_claim_identification_accuracy(self):
        with TemporaryDirectory() as td:
            clip = Path(td) / "sample.webm"
            clip.write_bytes(b"local fixture")
            cap = Capture()
            result = run_smoke(clip, Path(td), max_frames=4,
                               capture_factory=lambda p: cap, model_factory=FakeModel)
        self.assertEqual(result["version"], VERSION)
        self.assertEqual(result["testedFrames"], 4)
        self.assertEqual(result["horseObjectObservations"], 4)
        self.assertEqual(result["distinctTemporaryTrackIds"], 1)
        self.assertFalse(result["horseNumberRecognitionTested"])
        self.assertFalse(result["japaneseRaceForecastAccuracyProved"])
        self.assertFalse(result["predictionApplied"])
        self.assertTrue(cap.released)

    def test_dense_track_proxy_and_no_betting_claim(self):
        with TemporaryDirectory() as td:
            clip = Path(td) / "sample.webm"
            clip.write_bytes(b"local fixture")
            baseline = run_smoke(
                clip, Path(td), max_frames=4,
                capture_factory=lambda p: Capture(), model_factory=FakeModel)
            dense = run_smoke(
                clip, Path(td), max_frames=8, sample_hz=2,
                capture_factory=lambda p: Capture(), model_factory=FakeModel)
        self.assertEqual(baseline["sampleRateHz"], 1)
        self.assertEqual(dense["sampleRateHz"], 2)
        self.assertEqual(baseline["trackContinuityProxies"]["tracksWithAtLeast3Detections"], 1)
        self.assertEqual(dense["trackContinuityProxies"]["longestConsecutiveSampledFrames"], 8)
        report = compare(baseline, dense)
        self.assertEqual(report["dense"]["temporaryTrackIds"], 1)
        self.assertFalse(report["improvedHorseIdentityProven"])
        self.assertIsNone(report["horseIdentitySwitchRate"])
        with self.assertRaisesRegex(ValueError, "provenance"):
            modified = dict(dense, sourceVideoSha256="b" * 64)
            compare(baseline, modified)

    def test_direct_cc_download_with_bounded_size(self):
        with TemporaryDirectory() as td:
            target = Path(td) / "cc.webm"
            digest = download_cc_sample(target, opener=lambda *a, **k:
                                        FakeStream(b"x" * 11000))
            self.assertEqual(len(digest), 64)
            self.assertEqual(target.stat().st_size, 11000)
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "12 MB"):
                download_cc_sample(Path(td) / "too-big.webm",
                                   opener=lambda *a, **k: FakeStream(b"x" * 12_000_001))
