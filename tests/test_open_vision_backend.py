"""Apache RT-DETR and MIT ByteTrack infrastructure: offline safety contracts."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from arvexq.vision.open_detector import (
    COCO_HORSE_CLASS, DETECTOR_VERSION, RTDetrByteTracker, _Result,
)
from scripts.arvexq_fetch_open_vision_model import (
    MODEL_REPO, MODEL_REVISION, prepare_model,
)


class PermissiveVideoModelTests(TestCase):
    def test_pinned_model_is_public_apache_checkpoint(self):
        self.assertEqual(MODEL_REPO, "PekingU/rtdetr_r50vd")
        self.assertEqual(len(MODEL_REVISION), 40)
        self.assertIn("apache-rtdetr", DETECTOR_VERSION)
        self.assertEqual(COCO_HORSE_CLASS, 17)

    def test_model_download_is_pinned_and_only_contains_expected_files(self):
        calls = []
        with TemporaryDirectory() as td:
            def fake_fetch(**kwargs):
                calls.append(kwargs)
                for filename in kwargs["allow_patterns"]:
                    (Path(td) / filename).write_bytes(
                        b"---\nlicense: apache-2.0\n---\n" if filename == "README.md"
                        else b"mock nonempty file"
                    )
            result = prepare_model(td, fetcher=fake_fetch)
            self.assertEqual(result, Path(td))
            self.assertEqual(calls[0]["repo_id"], MODEL_REPO)
            self.assertEqual(calls[0]["revision"], MODEL_REVISION)
            self.assertEqual(sorted(calls[0]["allow_patterns"]), sorted(
                ["README.md", "config.json", "preprocessor_config.json", "model.safetensors"]))

    def test_reject_license_drift_or_incomplete_snapshot(self):
        with TemporaryDirectory() as td:
            def wrong_license(**kwargs):
                for filename in kwargs["allow_patterns"]:
                    (Path(td) / filename).write_text(
                        "license: restrictive" if filename == "README.md" else "mock")
            with self.assertRaisesRegex(ValueError, "Apache-2.0"):
                prepare_model(td, fetcher=wrong_license)
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                prepare_model(td, fetcher=lambda **kwargs: None)

    def test_camera_tracker_is_new_per_segment_and_no_network_required(self):
        with TemporaryDirectory() as td:
            a, b = RTDetrByteTracker(td), RTDetrByteTracker(td)
            self.assertIsNone(a._tracker)
            self.assertIsNone(b._tracker)
            a.set_frame_rate(25)
            self.assertEqual(a.fps, 25)
            with self.assertRaises(ValueError):
                a.set_frame_rate(0)
        x = _Result([13], [[1., 2., 3., 4.]], [0.99], [17])
        self.assertEqual(x.boxes.id.cpu().tolist(), [13])
        self.assertEqual(x.boxes.cls.cpu().tolist(), [17])
