"""Validate genuine original before-off tickets and retryable failed captures.

A failed computation is NOT a deliberate purchase "見送り".
A valid original is immutable. Only a failed/missing capture is eligible for
pre-off retry, with the original unsuccessful receipt retained separately.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any


def has_valid_original(bet: Any, *, race_id: str, start_at: datetime | None = None) -> bool:
    if not isinstance(bet, dict) or not isinstance(bet.get("items"), list):
        return False
    if str(bet.get("raceId") or "") != str(race_id or ""):
        return False
    if not bet.get("fixedAt") or bet.get("captureStatus") == "failed":
        return False
    if str(bet.get("decision") or "") in ("", "未取得", "エラー"):
        return False
    try:
        at = datetime.fromisoformat(str(bet["fixedAt"]).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if at.tzinfo is None:
        return False
    if start_at and (start_at.tzinfo is None or at >= start_at):
        return False
    return True


def record_failed_attempt(detail: dict[str, Any], previous: Any, *, message: str, fixed_at: str) -> dict[str, Any]:
    attempts = list(detail.get("preRaceBetCaptureFailures") or [])
    previous_is_failed = isinstance(previous, dict) and previous.get("captureStatus") == "failed"
    if previous_is_failed:
        prior = {"fixedAt": str(previous.get("fixedAt") or "")[:35],
                 "error": str(previous.get("captureError") or "")[:250]}
        if prior not in attempts:
            attempts.append(prior)
    failure = {"fixedAt": fixed_at[:35], "error": str(message)[:250]}
    if failure not in attempts:
        attempts.append(failure)
    # Bound growth for races whose data input is never usable before the off.
    detail["preRaceBetCaptureFailures"] = attempts[-24:]
    return {
        "raceId": str(detail.get("id") or ""), "fixedAt": fixed_at,
        "decision": "未取得", "items": [], "betQuality": None,
        "trifectaReviewed": False, "trifectaDecision": "未取得",
        "reason": "買い目の計算失敗。実際の見送り判断ではありません。",
        "captureStatus": "failed", "captureError": str(message)[:250],
        "lockPolicy": "server-js-ticket-v1-unavailable",
    }
