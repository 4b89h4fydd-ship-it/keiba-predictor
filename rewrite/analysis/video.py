"""Video-evidence gate for the rewrite.

Old-system research (docs/vision) established the rules this module
enforces mechanically:

- Open detector/tracker licences (RT-DETR Apache-2.0, ByteTrack MIT)
  do NOT grant rights to JRA/NAR race footage. An authorized feed must
  be recorded before any video is processed.
- A detector smoke test is not identity accuracy. Video-derived
  numbers may enter a forecast ONLY when a ground-truth benchmark —
  independently human-reviewed, with stable horse identities — passes
  the thresholds below on real race footage.
- Until then the gate is closed and forecasts carry
  ``video_status="not-applied"`` with the reason. Nothing is imputed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .calibration import LabelledRace, log_loss

POLICY = {
    "min_identity_f1": 0.90,
    "min_precision": 0.90,
    "min_recall": 0.90,
    "min_reviewed_races": 5,
}
MAX_TRIP_ADJUSTMENT = 0.10  # strength multiplier bounded to [0.90, 1.10]


@dataclass(frozen=True)
class BenchmarkRecord:
    dataset: str
    reviewed_races: int
    identity_f1: float
    precision: float
    recall: float
    independently_reviewed: bool
    feed_authorization: str  # reference to the authorized video source

    def failures(self) -> tuple:
        out = []
        if not self.feed_authorization.strip():
            out.append("no-authorized-video-feed")
        if not self.independently_reviewed:
            out.append("benchmark-not-independently-reviewed")
        if self.reviewed_races < POLICY["min_reviewed_races"]:
            out.append("too-few-reviewed-races")
        if self.identity_f1 < POLICY["min_identity_f1"]:
            out.append("identity-f1-below-threshold")
        if self.precision < POLICY["min_precision"]:
            out.append("precision-below-threshold")
        if self.recall < POLICY["min_recall"]:
            out.append("recall-below-threshold")
        return tuple(out)


@dataclass(frozen=True)
class VideoObservation:
    """Video-derived facts about ONE past run of ONE horse."""

    race_id: str
    horse_number: int
    trip_loss_m: Optional[float]  # estimated metres lost to wide trips/trouble
    start_delay: Optional[float]  # seconds lost at the start
    trouble: bool
    detector_version: str
    benchmark: BenchmarkRecord


@dataclass(frozen=True)
class VideoGate:
    open: bool
    reasons: tuple

    @property
    def status(self) -> str:
        return "applied-verified" if self.open else "not-applied"


def evaluate_gate(benchmark: Optional[BenchmarkRecord]) -> VideoGate:
    if benchmark is None:
        return VideoGate(False, ("no-benchmark-record", "no-authorized-video-feed"))
    failures = benchmark.failures()
    return VideoGate(not failures, failures)


def strength_adjustment(observations: list[VideoObservation]) -> float:
    """Bounded strength multiplier from admitted video observations.

    A horse repeatedly losing ground to trouble/trip is stronger than
    its bare finishing positions suggest: each metre of average trip
    loss adds 1% strength, each start delay of 0.1s adds 0.5%, capped.
    Only called when the gate is open.
    """
    losses = [o.trip_loss_m for o in observations if o.trip_loss_m is not None]
    delays = [o.start_delay for o in observations if o.start_delay is not None]
    factor = 1.0
    if losses:
        factor += 0.01 * (sum(losses) / len(losses))
    if delays:
        factor += 0.05 * (sum(delays) / len(delays))
    troubled = sum(1 for o in observations if o.trouble)
    if troubled:
        factor += 0.01 * troubled / max(1, len(observations))
    return max(1.0 - MAX_TRIP_ADJUSTMENT, min(1.0 + MAX_TRIP_ADJUSTMENT, factor))


def apply_video(
    strengths: dict[int, float],
    observations_by_horse: dict[int, list[VideoObservation]],
    benchmark: Optional[BenchmarkRecord],
) -> tuple[dict[int, float], VideoGate]:
    """Return (possibly adjusted strengths, gate). Closed gate = input."""
    gate = evaluate_gate(benchmark)
    if not gate.open:
        return dict(strengths), gate
    adjusted = dict(strengths)
    for number, observations in observations_by_horse.items():
        if number in adjusted and observations:
            adjusted[number] = adjusted[number] * strength_adjustment(observations)
    return adjusted, gate


def compare_with_without(
    races: list[LabelledRace],
    probs_without: Callable[[LabelledRace], dict],
    probs_with: Callable[[LabelledRace], dict],
) -> dict:
    """Video on/off comparison on labelled races (same races, both arms).

    Adoption rule (caller's responsibility, enforced by the rebuild
    plan): video stays out of production unless log loss improves on
    races not used to fit anything.
    """
    without = [LabelledRace(r.date, probs_without(r), r.winner, r.top3) for r in races]
    with_ = [LabelledRace(r.date, probs_with(r), r.winner, r.top3) for r in races]
    loss_without = log_loss(without)
    loss_with = log_loss(with_)
    return {
        "races": len(races),
        "log_loss_without_video": loss_without,
        "log_loss_with_video": loss_with,
        "delta": loss_with - loss_without,
        "improves": loss_with < loss_without,
    }
