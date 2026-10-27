"""Tests for the video evidence gate and A/B comparison harness."""
import unittest

from rewrite.analysis.calibration import LabelledRace
from rewrite.analysis.video import (
    BenchmarkRecord, VideoObservation, apply_video, compare_with_without,
    evaluate_gate, strength_adjustment,
)


def benchmark(**overrides):
    base = dict(
        dataset="reviewed-jra-nar-sample", reviewed_races=8,
        identity_f1=0.95, precision=0.96, recall=0.94,
        independently_reviewed=True, feed_authorization="feed-contract-2026",
    )
    base.update(overrides)
    return BenchmarkRecord(**base)


def observation(**overrides):
    base = dict(
        race_id="past-1", horse_number=1, trip_loss_m=3.0,
        start_delay=0.0, trouble=True, detector_version="rtdetr-test",
        benchmark=benchmark(),
    )
    base.update(overrides)
    return VideoObservation(**base)


class GateTests(unittest.TestCase):
    def test_no_benchmark_keeps_gate_closed(self):
        gate = evaluate_gate(None)
        self.assertFalse(gate.open)
        self.assertEqual(gate.status, "not-applied")

    def test_unreviewed_or_weak_benchmark_blocked(self):
        self.assertFalse(evaluate_gate(benchmark(independently_reviewed=False)).open)
        self.assertFalse(evaluate_gate(benchmark(identity_f1=0.80)).open)
        self.assertFalse(evaluate_gate(benchmark(reviewed_races=2)).open)
        gate = evaluate_gate(benchmark(feed_authorization=""))
        self.assertIn("no-authorized-video-feed", gate.reasons)

    def test_passing_benchmark_opens_gate(self):
        self.assertTrue(evaluate_gate(benchmark()).open)

    def test_closed_gate_returns_strengths_unchanged(self):
        strengths = {1: 1.0, 2: 2.0}
        adjusted, gate = apply_video(strengths, {1: [observation()]}, None)
        self.assertEqual(adjusted, strengths)
        self.assertFalse(gate.open)

    def test_open_gate_adjusts_within_bounds(self):
        strengths = {1: 1.0, 2: 2.0}
        adjusted, gate = apply_video(
            strengths, {1: [observation(trip_loss_m=50.0)]}, benchmark()
        )
        self.assertTrue(gate.open)
        self.assertGreater(adjusted[1], strengths[1])
        self.assertLessEqual(adjusted[1], strengths[1] * 1.10)
        self.assertEqual(adjusted[2], strengths[2])

    def test_adjustment_math(self):
        factor = strength_adjustment([observation(trip_loss_m=2.0, trouble=False)])
        self.assertAlmostEqual(factor, 1.02)


class CompareTests(unittest.TestCase):
    def test_compare_reports_delta(self):
        races = [LabelledRace("2026-10-01", {}, 1, (1,)) for _ in range(3)]
        result = compare_with_without(
            races,
            probs_without=lambda r: {1: 0.3, 2: 0.7},
            probs_with=lambda r: {1: 0.6, 2: 0.4},
        )
        self.assertTrue(result["improves"])
        self.assertLess(result["delta"], 0)


if __name__ == "__main__":
    unittest.main()
