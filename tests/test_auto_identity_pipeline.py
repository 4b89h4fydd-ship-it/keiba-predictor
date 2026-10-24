"""Auto OCR identity tests with deterministic mock frames, no network/download."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from arvexq.vision.auto_identity import resolve_ocr_identities
from arvexq.vision.video_detector import collect_video
from test_real_video_detector import FakeCapture, FakeModel, config


def reads(track=7, no=1, n=3, camera="camera-0", conf=.98):
    return [{"cameraId": camera, "trackId": track, "timeSeconds": float(i),
             "horseNumber": no, "confidence": conf} for i in range(n)]


class OcrConsensusTests(TestCase):
    def test_three_frames_consensus_accepts_correct_entry_only(self):
        mapped = resolve_ocr_identities(reads(), [1, 2])
        self.assertEqual(mapped["camera-0"]["7"]["horseNumber"], 1)
        self.assertFalse(mapped["camera-0"]["7"]["verified"])
        self.assertEqual(mapped["camera-0"]["7"]["voteShare"], 1.)

    def test_single_read_and_low_confidence_never_assign(self):
        self.assertEqual(resolve_ocr_identities(reads(n=2), [1, 2]), {})
        self.assertEqual(resolve_ocr_identities(reads(conf=.51), [1, 2]), {})

    def test_conflicting_ocr_and_wrong_number_refused(self):
        mixed = reads(n=2) + [{"cameraId": "camera-0", "trackId": 7,
                              "timeSeconds": 2., "horseNumber": 2, "confidence": .99}]
        self.assertEqual(resolve_ocr_identities(mixed, [1, 2]), {})
        self.assertEqual(resolve_ocr_identities(reads(no=8), [1, 2]), {})

    def test_two_tracks_claiming_same_horse_both_rejected(self):
        self.assertEqual(resolve_ocr_identities(reads(track=7) + reads(track=8), [1, 2]),
                         {"camera-0": {}})

    def test_duplicate_frame_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate OCR"):
            resolve_ocr_identities(reads() + [deepcopy(reads()[0])], [1, 2])


class InternalVideoIdentityTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.video = Path(self.tmp.name, "video.mp4")
        self.weights = Path(self.tmp.name, "weights.pt")
        self.video.write_bytes(b"fixture video only")
        self.weights.write_bytes(b"fixture weights only")
        self.capture = FakeCapture()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, reader):
        cfg = config()
        cfg["autoIdentifySaddlecloth"] = True
        cfg["verifiedIdentityMap"] = {}
        return collect_video(self.video, cfg, model_path=self.weights,
                             capture_factory=lambda _: self.capture,
                             model_factory=FakeModel, ocr_reader=reader)

    def test_internal_ocr_can_resolve_horses_without_user_view(self):
        def fake_ocr(frame, bounds):
            # Mock saddlecloth number determined from bounding-box vertical row.
            return {"horseNumber": 1 if bounds[3] == 1.0 else 2,
                    "confidence": .99}
        result = self._run(fake_ocr)
        rows = result["measurements"]["runners"]
        self.assertEqual([r["observedFrames"] for r in rows], [3, 3])
        self.assertEqual(result["manifest"]["capture"]["autoIdentifiedDetections"], 6)
        self.assertEqual(result["manifest"]["capture"]["unidentifiedDetections"], 0)
        self.assertTrue(all(h["identitySource"] == "automated-ocr-provisional"
                            for f in result["manifest"]["frames"] for h in f["horses"]))
        self.assertFalse(result["predictionApplied"])

    def test_ambiguous_reads_do_not_fabricate_horse_identity(self):
        report = self._run(lambda frame, bounds: None)
        self.assertEqual(report["manifest"]["capture"]["autoIdentifiedDetections"], 0)
        self.assertEqual(report["manifest"]["capture"]["unidentifiedDetections"], 6)
        self.assertEqual(report["measurements"]["runners"][0]["observedFrames"], 0)
