"""Measured per-kind betting returns based exclusively on official payouts."""
from __future__ import annotations
import re
from typing import Any


def parse_official_payouts(result: dict[str, Any]):
    # Per-100-yen actual payout only when the official result contains a
    # complete parseable entry for the specific ticket kind. Never impute
    # returns from win odds or missing payout types.
    official_payouts = {}
    payout_invalid = set()
    for row in result.get("payouts") or []:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("type") or "")
        if not kind:
            continue
        raw = str(row.get("combination") or "")
        numbers = [int(x) for x in re.findall(r"\d+", raw)]
        expected = 3 if kind in {"3連単", "3連複"} else 2 if kind in {"ワイド", "馬連", "馬単"} else 1 if kind == "単勝" else 0
        raw_amount = row.get("amount")
        try:
            amount = int(str(raw_amount).replace(",", "").replace("円", "").replace("¥", "").strip())
        except (TypeError, ValueError):
            amount = -1
        if not expected or len(numbers) != expected or amount < 0:
            payout_invalid.add(kind)
            continue
        if kind in {"ワイド", "馬連", "3連複"}:
            numbers.sort()
        official_payouts.setdefault(kind, {})[tuple(numbers)] = amount

    return official_payouts, payout_invalid


def ticket_payout(kind, combos, official_payouts, payout_invalid):
    prices = official_payouts.get(kind)
    payout = None
    if prices and kind not in payout_invalid:
        payout = 0
        for raw in combos:
            try:
                values = [int(x) for x in raw]
            except (TypeError, ValueError):
                payout = None
                break
            if kind in {"ワイド", "馬連", "3連複"}:
                values.sort()
            payout += prices.get(tuple(values), 0)
    return payout

def summarize_frozen_ticket_metrics(audits: list[dict[str, Any]]) -> dict[str, Any]:
    """Kind-specific historical performance for validated sealed, final races.

    A hit rate here is an observed sample fraction, never an AI-predicted chance.
    ROI is a simulated flat 100-yen-per-ticket return, NOT actual purchases.
    One missing payout invalidates the entire kind's return estimate.
    """
    kinds: dict[str, dict[str, Any]] = {}
    for audit in audits:
        if not isinstance(audit, dict) or audit.get("version") != "arvexq-frozen-result-audit-v1":
            continue
        for item in audit.get("ticketEvaluations") or []:
            if not isinstance(item, dict) or not item.get("kind"):
                continue
            kind = str(item["kind"])
            points = int(item.get("points") or 0)
            if points < 1:
                continue
            group = kinds.setdefault(kind, {"races": 0, "hits": 0,
                "points": 0, "stakeYenAt100": 0, "payoutYenAt100": 0,
                "completePayouts": True, "payoutObserved": 0})
            group["races"] += 1
            group["hits"] += int(bool(item.get("hit")))
            group["points"] += points
            group["stakeYenAt100"] += 100 * points
            amount = item.get("payoutYenAt100")
            if amount is None:
                group["completePayouts"] = False
            else:
                group["payoutYenAt100"] += int(amount)
                group["payoutObserved"] += 1
    response: dict[str, Any] = {}
    for kind, group in sorted(kinds.items()):
        complete = group["completePayouts"] and group["payoutObserved"] == group["races"]
        response[kind] = {
            "sampleRaces": group["races"],
            "hits": group["hits"],
            "observedHitRate": group["hits"] / group["races"],
            "averagePoints": group["points"] / group["races"],
            "stakeYenAt100": group["stakeYenAt100"],
            "payoutYenAt100": group["payoutYenAt100"] if complete else None,
            "flatStakeReturnRate": (
                group["payoutYenAt100"] / group["stakeYenAt100"]
                if complete and group["stakeYenAt100"] else None
            ),
            "completePayouts": complete,
        }
    return {"version": "arvexq-archived-ticket-metrics-v1",
            "stakeBasis": "simulated-100-yen-per-combination-not-real-purchases",
            "byKind": response}
