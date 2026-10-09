#!/usr/bin/env python3
"""Read-only scorecard for ORIGINAL pre-off bets; never replay after the result.

The denominator is all scheduled races. Missing/capture-failed records are
never silently called deliberate "見送り". Returns from the official result
are measured only for race-level original frozen tickets.
"""
from __future__ import annotations
from collections import Counter
from typing import Any

VALID_KINDS = {"ワイド", "馬連", "馬単", "3連複", "3連単", "単勝"}


def skip_reason(text: str) -> str:
    reason = str(text or "")
    for name, terms in (
        ("unavailable-input", ("データ不足", "データ未取得", "未充足", "未取得", "取得不可", "データ充足", "馬場情報")),
        ("pace-evidence", ("位置取り", "先行", "展開根拠", "隊列", "ペース")),
        ("winner-uncertain", ("◎なし", "軸なし", "1着候補", "勝ち馬", "着順")),
        ("market-unavailable", ("オッズ", "馬体重", "期待値")),
        ("selection-gate", ("厳選", "選定", "品質", "審査", "条件未達", "不成立", "集中度")),
    ):
        if any(term in reason for term in terms):
            return name
    return "unspecified"


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    state: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    tickets: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    lane_counts: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    settled, axis = 0, Counter()
    for report in reports:
        if not isinstance(report, dict):
            continue
        status = str(report.get("status") or "unknown")
        state[status] += 1
        if status != "sealed":
            continue
        ticket_state = str(report.get("ticket") or "missing")
        tickets[ticket_state] += 1
        lane = str(report.get("morning_primary_type") or "")
        if lane:
            lane_counts[lane] += 1
        if ticket_state != "recorded":
            continue
        decision = str(report.get("bet_decision") or "")
        items = [k for k in report.get("bet_item_kinds") or [] if k in VALID_KINDS]
        if items and decision != "見送り":
            tickets["issued"] += 1
            for kind in set(items):
                kinds[kind] += 1
        else:
            tickets["intentional-skip"] += 1
            reasons[skip_reason(report.get("bet_reason") or "")] += 1
        for w in report.get("bet_input_warnings") or []:
            warnings[str(w)[:100]] += 1
        audit = report.get("ticket_result")
        if isinstance(audit, dict) and audit.get("version") == "arvexq-frozen-result-audit-v1":
            settled += 1
            if audit.get("honmeiPresent"):
                axis["with-◎"] += 1
                axis["◎-top3"] += int(audit.get("honmeiTop3Hit") is True)
                axis["◎-win"] += int(audit.get("honmeiWinHit") is True)
    with_axis = axis["with-◎"]
    issued, skipped = tickets["issued"], tickets["intentional-skip"]
    return {
        "version": "arvexq-preoff-ticket-funnel-v1",
        "scope": "original-server-preoff-bets-no-after-race-replay",
        "scheduledRaces": sum(state.values()),
        "sealedRaces": state["sealed"],
        "recordedBets": tickets["recorded"],
        "issuedRaces": issued,
        "intentionalSkippedRaces": skipped,
        "unavailableOrInvalidBets": state["sealed"] - tickets["recorded"],
        "issueRateAmongRecorded": issued / (issued + skipped) if issued + skipped else None,
        "byTicketKind": dict(sorted(kinds.items())),
        "skipReasons": dict(sorted(reasons.items())),
        "unavailableByStatus": dict(sorted((k, v) for k, v in tickets.items()
                                            if k not in {"recorded", "issued", "intentional-skip"})),
        "raceStatusCounts": dict(sorted(state.items())),
        "morningTypesWithAuditablePreoffBet": dict(sorted(lane_counts.items())),
        "missingInputWarnings": dict(sorted(warnings.items())),
        "finalResultEvaluatedRaces": settled,
        "honmei": {
            "evaluatedFinalRacesWithMark": with_axis,
            "top3Hits": axis["◎-top3"],
            "winHits": axis["◎-win"],
            "top3ObservedRate": axis["◎-top3"] / with_axis if with_axis else None,
            "winObservedRate": axis["◎-win"] / with_axis if with_axis else None,
        },
    }
