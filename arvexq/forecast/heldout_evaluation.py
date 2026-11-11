"""Read-only evaluation runner for immutable pre-race forecast snapshots.

No prediction model is called here. Evaluations require the exact archived
ordered-top3 probabilities, observed finish order and independently observed
timestamps. Failed/invalid races are reported, never counted as successes.
"""
from __future__ import annotations

from collections import Counter

from arvexq.forecast.validation_metrics import evaluate_race, summarize_results


def evaluate_archived_races(records):
    """Return sample/coverage-aware metrics for a held-out archived set.

    Each record: raceId, orderedTop3, finishOrder, predictionCutoff, offTime.
    Race IDs must be unique; a duplicate fails the entire batch instead of
    silently inflating the reported sample. Missing predictions and dead heats
    are not guessed. No decision about production readiness is made.
    """
    if not isinstance(records, list):
        return None
    ids = [r.get("raceId") if isinstance(r, dict) else None for r in records]
    if any(not isinstance(rid, str) or not rid.strip() for rid in ids):
        return None
    if len(ids) != len(set(ids)):
        return None

    reasons = Counter()
    scored = []
    for record in records:
        if not isinstance(record.get("orderedTop3"), list):
            reasons["missing_pre_race_forecast"] += 1
            continue
        result = evaluate_race(
            record["orderedTop3"], record.get("finishOrder"),
            prediction_cutoff=record.get("predictionCutoff"),
            off_time=record.get("offTime"),
        )
        if result is None:
            reasons["invalid_snapshot_or_result"] += 1
            continue
        scored.append(result)
    return {
        "totalRaces": len(records),
        "evaluatedRaces": len(scored),
        "coverage": len(scored) / len(records) if records else 0,
        "exclusions": dict(sorted(reasons.items())),
        "metrics": summarize_results(scored),
        "productionApproved": False,
    }
