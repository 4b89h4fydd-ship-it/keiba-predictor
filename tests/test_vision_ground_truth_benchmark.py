"""Tracking ground-truth benchmark: positives, ID switches, failure-closed."""
from __future__ import annotations

from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path
import json
from unittest import TestCase

from arvexq.vision.benchmark import evaluate_labels, _optimal_pairs
from scripts.arvexq_vision_benchmark import template_from_video, main

HASH = "e" * 64


def box(a=0, b=0):
    return [a, b, a + 10, b + 10]


def frame(s, *tracks):
    return {"seconds": float(s),
            "tracks": [{"trackId": tid, "bbox": box(x, 0)}
                       for tid, x in tracks]}


def truth_frame(s, *horses):
    return {"seconds": float(s),
            "horses": [{"horseId": hid, "bbox": box(x, 0)}
                       for hid, x in horses]}


def predicted(*frames):
    return {"sourceVideoSha256": HASH, "sourcePage": "https://commons.wikimedia.org",
            "observedFrames": list(frames), "predictionApplied": False}


def ground_truth(*frames):
    return {"videoSha256": HASH,
            "annotation": {"method": "independent-manual-review",
                           "reviewed": True, "annotator": "test-fixture-reviewer",
                           "version": "fixture-v1", "usedModelPredictionsAsTruth": False},
            "frames": list(frames)}


class GroundTruthBenchmarkTests(TestCase):
    def test_perfect_geometric_detection_and_idf1(self):
        p = predicted(frame(1, (7, 0), (8, 30)),
                      frame(2, (7, 2), (8, 32)))
        t = ground_truth(truth_frame(1, ("alpha", 0), ("beta", 30)),
                         truth_frame(2, ("alpha", 2), ("beta", 32)))
        r = evaluate_labels(p, t)
        self.assertEqual(r["matchedHorseInstances"], 4)
        self.assertEqual(r["detectionRecallAtIou"], 1)
        self.assertEqual(r["detectionPrecisionAtIou"], 1)
        self.assertEqual(r["identityF1"], 1)
        self.assertEqual(r["adjacentMatchedIdentitySwitches"], 0)
        self.assertFalse(r["provenForJapan"])
        self.assertFalse(r["productionPredictionApplied"])

    def test_split_track_id_detects_identity_switch_and_degrades_idf1(self):
        p = predicted(frame(1, (7, 0)), frame(2, (7, 2)),
                      frame(3, (9, 4)), frame(4, (9, 6)))
        t = ground_truth(*(truth_frame(i, ("horse-A", 2*(i-1)))
                           for i in range(1, 5)))
        r = evaluate_labels(p, t)
        self.assertEqual(r["detectionRecallAtIou"], 1)
        self.assertEqual(r["identityF1"], .5)
        self.assertEqual(r["adjacentMatchedIdentitySwitches"], 1)
        self.assertEqual(r["identityTruePositives"], 2)

    def test_missing_and_false_horses_are_counted(self):
        p = predicted(frame(1, (7, 0), (8, 60)), frame(2))
        t = ground_truth(truth_frame(1, ("a", 0), ("b", 30)),
                         truth_frame(2, ("a", 0), ("b", 30)))
        r = evaluate_labels(p, t)
        self.assertEqual(r["truthHorseInstances"], 4)
        self.assertEqual(r["predictedTrackInstances"], 2)
        self.assertEqual(r["matchedHorseInstances"], 1)
        self.assertEqual(r["falsePositiveTrackInstances"], 1)
        self.assertEqual(r["missedHorseInstances"], 3)
        self.assertEqual(r["detectionPrecisionAtIou"], .5)
        self.assertEqual(r["detectionRecallAtIou"], .25)
        self.assertEqual(r["identityF1"], .33333)

    def test_no_predictions_are_not_perfect_precision(self):
        p = predicted(frame(1))
        t = ground_truth(truth_frame(1, ("a", 0)))
        r = evaluate_labels(p, t)
        self.assertIsNone(r["detectionPrecisionAtIou"])
        self.assertEqual(r["detectionRecallAtIou"], 0)
        self.assertEqual(r["identityF1"], 0)

    def test_hungarian_prefers_two_valid_matches_to_one_large_iou(self):
        self.assertEqual(len(_optimal_pairs([[101., 100.01], [100.01, 0.]])), 2)

    def test_refuses_self_label_or_unreviewed_data(self):
        p = predicted(frame(1, (7, 0)))
        t = ground_truth(truth_frame(1, ("a", 0)))
        t["annotation"]["usedModelPredictionsAsTruth"] = True
        with self.assertRaisesRegex(ValueError, "independent"):
            evaluate_labels(p, t)
        t["annotation"]["usedModelPredictionsAsTruth"] = False
        t["annotation"]["reviewed"] = False
        with self.assertRaisesRegex(ValueError, "independent"):
            evaluate_labels(p, t)

    def test_refuses_mismatched_frames_source_and_duplicate_id(self):
        p = predicted(frame(1, (7, 0)))
        t = ground_truth(truth_frame(1, ("a", 0)))
        modified = deepcopy(t)
        modified["videoSha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "SHA256"):
            evaluate_labels(p, modified)
        modified = ground_truth(truth_frame(2, ("a", 0)))
        with self.assertRaisesRegex(ValueError, "every sampled frame"):
            evaluate_labels(p, modified)
        modified = ground_truth(truth_frame(1, ("a", 0), ("a", 30)))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate_labels(p, modified)

    def test_no_annotations_is_not_a_benchmark(self):
        p = predicted(frame(1, (7, 0)))
        template = template_from_video(p)
        self.assertFalse(template["annotation"]["reviewed"])
        self.assertEqual(template["frames"], [{"seconds": 1., "horses": []}])
        with self.assertRaisesRegex(ValueError, "independent"):
            evaluate_labels(p, template)

    def test_cli_serializes_template_but_not_a_false_accuracy(self):
        with TemporaryDirectory() as td:
            folder = Path(td)
            prediction = folder / "sample.json"
            template = folder / "truth-template.json"
            report = folder / "score.json"
            prediction.write_text(json.dumps(predicted(frame(1, (7, 0)))))
            self.assertEqual(main(["--prediction", str(prediction),
                                   "--template", "--output", str(template)]), 0)
            with self.assertRaisesRegex(ValueError, "independent"):
                main(["--prediction", str(prediction),
                      "--truth", str(template), "--output", str(report)])
            self.assertFalse(report.exists())
