"""Explicit approval-gated pre-off forecast from observed recent finishing places.

This is a conservative baseline, not a validated learned AI or an 80% guarantee.
No results, archived forecasts, market odds, or fabricated history are used.
"""
from datetime import datetime
from math import exp, log
from zoneinfo import ZoneInfo
from hashlib import sha256
from random import Random

VERSION = "arvexq-observed-history-baseline-v1"
JST = ZoneInfo("Asia/Tokyo")
FINISH_KEYS = ("finish", "finishPosition", "rank", "place", "着順")


def _finish(run):
    if not isinstance(run, dict):
        return None
    for key in FINISH_KEYS:
        value = str(run.get(key, "")).strip().replace("着", "")
        if value.isascii() and value.isdigit():
            v = int(value)
            if v > 0:
                return v
    return None


def _start_time(facts):
    try:
        return datetime.fromisoformat(str(facts["date"]) + "T" + str(facts["startTime"])[:5]).replace(tzinfo=JST)
    except (TypeError, ValueError, KeyError):
        return None


def build_prediction(facts, now=None):
    """Return a detached, normalized joint scenario distribution or None.

    Only known starters with 3+ observed past finishes are considered; if one
    active horse lacks evidence, abstain rather than silently exclude it.
    """
    if not isinstance(facts, dict):
        return None
    start = _start_time(facts)
    moment = now or datetime.now(JST)
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if start is None or moment.astimezone(JST) >= start:
        return None
    horses = [h for h in facts.get("horses", []) if isinstance(h, dict)
              and not h.get("scratched") and not h.get("withdrawn")
              and str(h.get("status", "")).strip() not in ("取消", "除外", "競走除外")]
    if not 3 <= len(horses) <= 18:
        return None
    identifiers = [str(h.get("horseNumber", "")) for h in horses]
    if len(set(identifiers)) != len(identifiers) or not all(x.isdigit() and int(x) > 0 for x in identifiers):
        return None
    abilities = []
    for h in horses:
        runs = h.get("recentRaces") or h.get("allPastRuns") or []
        finish = [_finish(r) for r in runs[:8]]
        finish = [v for v in finish if v is not None]
        if len(finish) < 3:
            return None
        # Laplace-smoothed proxy, not calibrated winning probabilities.
        weights = [0.85 ** i for i in range(len(finish))]
        quality = sum(w / (1.0 + max(0, rank - 1) * 0.42)
                      for w, rank in zip(weights, finish)) / sum(weights)
        abilities.append(max(0.08, quality))
    # Full race permutations are intractable; deterministic seeded scenario
    # sampling prevents client changes across refreshes of identical facts.
    seed_material = repr((facts.get("id"), tuple(zip(identifiers, abilities)))).encode("utf-8")
    rng = Random(int.from_bytes(sha256(seed_material).digest()[:8], "big"))
    counts = {}
    samples = 2048
    for _ in range(samples):
        scores = []
        for h, a in zip(identifiers, abilities):
            u = max(1e-12, min(1 - 1e-12, rng.random()))
            scores.append((log(a) - log(-log(u)), h))
        order = tuple(h for _, h in sorted(scores, reverse=True))
        counts[order] = counts.get(order, 0) + 1
    scenarios = [(list(order), count / samples) for order, count in sorted(counts.items())]
    return {"version": VERSION, "raceId": str(facts.get("id") or ""),
            "scenarios": scenarios, "runnerCount": len(horses),
            "evidence": {"minPastFinishesPerRunner": 3, "samples": samples,
                         "calibrated": False, "method": "recent-rank baseline"},
            "predictionStatus": "provisional"}
