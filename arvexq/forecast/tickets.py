"""Ticket generation from one shared joint order distribution.

No odds => only probabilities, not a misleading profitability claim.
"""
from arvexq.prediction.recommendation_engine import recommend


def generate_tickets(prediction, marks, quoted_odds=None, min_hit_probability=0.8,
                     place_payout_slots=3):
    if not isinstance(prediction, dict) or not prediction.get("scenarios") or not marks:
        return []
    if not quoted_odds:
        return []
    result = recommend(prediction["scenarios"], quoted_odds,
                       max_tickets=4, min_hit_probability=min_hit_probability,
                       min_expected_return=1.0,
                       place_payout_slots=place_payout_slots)
    return result["tickets"] if result["status"] == "recommended" else []
