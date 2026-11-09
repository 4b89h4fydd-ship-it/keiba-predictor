"""Three research-only ticket styles using exact joint finish probabilities.

No bookmaker-odds fabrication, no unvalidated EV, no invented hit rate.
The existing R24 production / B36 control logic is intentionally untouched.
"""
from __future__ import annotations

from ..safety.probability import distribution, ticket_probability
from .forecast import RaceForecast


def ticket_styles(candidate: RaceForecast, assessment: dict) -> dict:
    styles = {"hit_first": None, "balanced": None, "outsider": None}
    if candidate.status != "ok" or assessment.get("status") != "shadow-candidate":
        return {"status": "insufficient-forecast", "styles": styles,
                "calibrationValidated": False, "stakeAllocationYen": None}
    strengths = {r.number: r.strength for r in candidate.runners
                 if r.strength is not None and r.strength > 0}
    n = len(strengths)
    if n < 3:
        return {"status": "insufficient-runners", "styles": styles,
                "calibrationValidated": False, "stakeAllocationYen": None}
    outcomes = distribution(strengths)
    best_top3 = sorted(candidate.runners, key=lambda r: (-r.p_top3, r.number))
    by_mark = {r.mark: r.number for r in candidate.runners if r.mark}
    place_count = 3 if n >= 8 else 2 if n >= 5 else 0

    def make(kind: str, legs: tuple, *, payout_places: int = 3) -> dict:
        p = ticket_probability(outcomes, kind, legs, place_count=payout_places)
        return {"kind": kind, "selection": list(legs), "modelHitProbability": round(p, 4),
                "probabilityStatus": "experimental-uncalibrated",
                "expectedReturn": None, "minimumActualOdds": None,
                "purchaseRecommended": False}

    if place_count:
        styles["hit_first"] = make("place", (best_top3[0].number,),
                                   payout_places=place_count)
        styles["balanced"] = make("wide", tuple(sorted(
            (best_top3[0].number, best_top3[1].number))))
        star = by_mark.get("☆")
        honmei = by_mark.get("◎")
        # The outsider arm requires observable market undervaluation.
        # No arbitrary longshot is filled in to meet a quota.
        eligible = {r["horseNumber"] for r in assessment.get("runners", ())
                    if r.get("valueHypothesis") and r.get("score100") is not None}
        if star in eligible and honmei is not None:
            styles["outsider"] = make("wide", tuple(sorted((honmei, star))))
    else:
        styles["hit_first"] = make("win", (best_top3[0].number,))
        styles["balanced"] = None
    return {
        "status": "conditional-research-only",
        "styles": styles,
        "twoHeadFixedHedge": styles["balanced"],
        "calibrationValidated": False,
        "stakeAllocationYen": None,
        "reason": "No certified held-out calibration or complete real payout odds; "
                  "candidate tickets are comparisons, not purchase advice",
    }
