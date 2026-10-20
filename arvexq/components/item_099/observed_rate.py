"""Observed 先行 proportion only; no inference or retrospective estimation."""
from math import isfinite

_RATE_KEYS = ("先行率", "front", "frontRate")


def read(horse):
    if not isinstance(horse, dict):
        return None
    for group in ("styleRates", "runningStyleRates"):
        rates = horse.get(group)
        if not isinstance(rates, dict):
            continue
        for key in _RATE_KEYS:
            value = rates.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if isfinite(value) and 0 <= value <= 100:
                return value
    return None
