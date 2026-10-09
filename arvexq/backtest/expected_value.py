"""Ticket value matrix only with pre-race odds AND independently calibrated probabilities."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def value_matrix(items: list[dict[str, Any]], *, calibration: dict[str, Any],
                 offered_odds: dict[str, float], odds_captured_at: str,
                 scheduled_post_at: str) -> dict[str, Any]:
    """Probabilities are per unique ticket outcome, not internal relative weights.

    Decimal tote odds are theoretical payouts per 1 unit, not the final dividend.
    """
    result: dict[str, Any] = {"status": "not-estimable", "rows": [], "version": "arvexq-value-matrix-v1"}
    try:
        cutoff = datetime.fromisoformat(scheduled_post_at.replace("Z", "+00:00"))
        observed = datetime.fromisoformat(odds_captured_at.replace("Z", "+00:00"))
        if not cutoff.tzinfo or not observed.tzinfo or observed >= cutoff:
            return result
    except (TypeError, ValueError, AttributeError):
        return result
    if calibration.get("method") != "out-of-sample" or calibration.get("validated") is not True:
        result["reason"] = "out-of-sample校正済み確率が未取得"
        return result
    result["status"] = "partial"
    for ticket in items:
        kind = str(ticket.get("kind") or "")
        for combo in ticket.get("combos") or []:
            key = kind + ":" + "-".join(str(n) for n in combo)
            prob = (calibration.get("ticketProbabilities") or {}).get(key)
            odds = offered_odds.get(key)
            if type(prob) not in (int, float) or type(odds) not in (int, float):
                continue
            if not 0 < prob < 1 or not 1 < odds < 100000:
                continue
            result["rows"].append({
                "kind": kind, "combo": combo, "probability": prob,
                "decimalOdds": odds, "expectedReturnRatio": round(prob * odds, 6),
                "expectedNetRatio": round(prob * odds - 1, 6),
                "meaning": "theoretical-preoff-not-observed-profit",
            })
    result["status"] = "ready" if result["rows"] and len(result["rows"]) == sum(
        len(x.get("combos") or []) for x in items) else "partial"
    return result
