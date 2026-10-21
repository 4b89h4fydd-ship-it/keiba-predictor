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
    # Compare registered ability arms on the SAME pre-off fact set.
    # This adds evidence INSIDE the six existing stages; it neither changes
    # the baseline pick nor promotes unverified recommendations.
    _attach_registered_method_consensus(facts, owner, result)
    # No inferred probability calibration, A/B/C grade or product betting policy.
    return result


# A registered cross-method comparison inspired by public specialist-AI methods.
# No provider forecasts, fetched odds, new scores, or fitted model weights.
# All three arms are already present in Stage64's research protocol; its code
# hash and pre-registered candidate algorithms remain completely unchanged.
_REGISTERED_ABILITY_ARMS = ("baseline", "recent5", "recent5_shrunk")


def _attach_registered_method_consensus(facts, owner, baseline):
    """Add unvalidated comparison evidence inside existing six-stage output.

    Majority is a diagnostic only. The officially selected baseline winRole,
    axisRole, uncalibrated probabilities, tickets and recommendation blocker
    are intentionally unchanged. An incomplete arm is never imputed.
    """
    from collections import Counter

    arms = {"baseline": baseline}
    try:
        for method in _REGISTERED_ABILITY_ARMS[1:]:
            arms[method] = predict(facts, expected_circuit=owner, ability_method=method)
    except (ValueError, TypeError, KeyError, AttributeError):
        return
    stage_names = ("ability", "runningStyle", "pace", "probability", "marks", "tickets")
    for method in _REGISTERED_ABILITY_ARMS:
        candidate = arms.get(method)
        if (not isinstance(candidate, dict)
                or candidate.get("raceId") != baseline.get("raceId")
                or candidate.get("date") != baseline.get("date")
                or candidate.get("circuit") != owner
                or candidate.get("abilityMethod") != method
                or candidate.get("modelVersion") != baseline.get("modelVersion")):
            return
        stages = candidate.get("stages")
        if (not isinstance(stages, dict) or
                any(not isinstance(stages.get(k), dict) or stages[k].get("value") is None
                    for k in stage_names)):
            return

    def picked(method, role):
        return arms[method]["stages"]["marks"]["value"][role]["horseNumber"]

    winners = {m: picked(m, "winRole") for m in _REGISTERED_ABILITY_ARMS}
    axes = {m: picked(m, "axisRole") for m in _REGISTERED_ABILITY_ARMS}
    if any(type(n) is not int or n <= 0 for n in list(winners.values()) + list(axes.values())):
        return
    roster = set(baseline["stages"]["ability"]["value"])
    if any(no not in roster for no in list(winners.values()) + list(axes.values())):
        return

    def majority(votes):
        n, count = Counter(votes.values()).most_common(1)[0]
        return n if count >= 2 else None

    win_values = {m: arms[m]["stages"]["probability"]["value"]["win"]
                  for m in _REGISTERED_ABILITY_ARMS}
    if any(set(values) != roster for values in win_values.values()):
        return
    ticket_lists = {m: arms[m]["stages"]["tickets"]["value"]["hypotheticalTrifectaTop10"]
                    for m in _REGISTERED_ABILITY_ARMS}
    if any(not isinstance(combos, list) for combos in ticket_lists.values()):
        return
    # Keep the existing baseline order; include only tickets supported by
    # 2+ of the three already-registered methods. This is NOT a bet.
    ticket_sets = {m: set(map(tuple, combos)) for m, combos in ticket_lists.items()}
    common = [combo for combo in ticket_lists["baseline"]
              if sum(tuple(combo) in ticket_sets[m] for m in _REGISTERED_ABILITY_ARMS) >= 2]
    if len({tuple(combo) for combo in common}) != len(common):
        return

    stages = baseline["stages"]
    stages["ability"]["registeredMethodComparison"] = {
        "status": "research-only-unvalidated",
        "arms": list(_REGISTERED_ABILITY_ARMS),
        "values": {m: arms[m]["stages"]["ability"]["value"]
                   for m in _REGISTERED_ABILITY_ARMS},
    }
    stages["probability"]["registeredMethodWinRangeUncalibrated"] = {
        no: {"min": min(win_values[m][no] for m in _REGISTERED_ABILITY_ARMS),
             "max": max(win_values[m][no] for m in _REGISTERED_ABILITY_ARMS)}
        for no in sorted(roster)
    }
    stages["marks"]["value"]["registeredMethodConsensus"] = {
        "status": "research-only-unvalidated",
        "winByMethod": winners,
        "axisByMethod": axes,
        "majorityWinCandidate": majority(winners),
        "majorityAxisCandidate": majority(axes),
        "baselineWinRoleUnchanged": True,
        "baselineAxisRoleUnchanged": True,
    }
    stages["tickets"]["value"]["registeredMethodConsensus"] = {
        "status": "research-only-unvalidated",
        "sharedTop10Candidates": common,
        "sharedTop10Count": len(common),
        "recommendedBetsPromoted": False,
    }
