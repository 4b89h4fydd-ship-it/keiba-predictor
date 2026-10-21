"""Stage64 six-stage forecast entrypoint for the existing ARVEXQ production boundary.

The previously rejected observed-rank engine remains retired. This module
invokes only the preserved Stage63/64 research implementation. A calculated
candidate is NOT a verified product mark or recommended ticket.
"""
from __future__ import annotations

from datetime import datetime
from datetime import timedelta, timezone
from arvexq.research.stage64.circuits import circuit
from arvexq.research.stage64.pipeline import predict

VERSION = "arvexq-stage64-six-stage-jra-nar-v1"


def build_prediction(facts, now=None):
    """Run the registered JRA/NAR six stages on genuine pre-off facts only.

    No new data fetch, alternate scorer, score imputation or post-race
    recomputation. An incomplete field remains unavailable.
    """
    if not isinstance(facts, dict):
        return None
    # A D1 pre-off race often has a placeholder {"status":"未確定",
    # "finishers":[]}. That is not an outcome; it must not block a forecast.
    # Actual result, payout or finished-state evidence still fails closed.
    if facts.get("results") or facts.get("payouts"):
        return None
    outcome = facts.get("result")
    if isinstance(outcome, dict):
        if (outcome.get("finishers") or outcome.get("payouts")
                or str(outcome.get("status") or "").strip().lower()
                in ("確定", "速報", "final", "confirmed", "official")):
            return None
    elif outcome:
        return None
    # Lazy import avoids the prediction package initializer's observed_model cycle.
    from arvexq.prediction.prerace_archive import post_at
    jst = timezone(timedelta(hours=9))
    stamp = now if now is not None else datetime.now(jst)
    off = post_at(facts)
    if not off or stamp.tzinfo is None or stamp.astimezone(jst) >= off:
        return None
    try:
        owner = circuit(facts)
        result = predict(facts, expected_circuit=owner)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
    # No inferred probability calibration, A/B/C grade or product betting policy.
    return result
