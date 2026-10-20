"""Canonical responsibility 161: caller-supplied timestamp freshness, no eviction or I/O."""
from __future__ import annotations

from math import isfinite
from typing import Any

def freshness(saved_at_epoch: Any, *, now_epoch: Any, ttl_seconds: Any) -> str:
    """Pure classification based only on caller-supplied timestamps.

    Missing timestamps stay unknown, never 'fresh'. Equality at expiry is stale.
    No arbitrary default TTL, no eviction and no networking.
    """
    def valid(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            n = float(value)
            return n if isfinite(n) else None
        except (TypeError, ValueError):
            return None

    now = valid(now_epoch)
    saved = valid(saved_at_epoch)
    ttl = valid(ttl_seconds)
    if ttl is None or ttl < 0:
        raise ValueError("nonnegative TTL required")
    if saved is None or now is None or saved <= 0 or now < 0:
        return "unknown"
    if saved > now:
        return "clock-conflict"
    return "fresh" if now - saved < ttl else "stale"
