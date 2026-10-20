"""Independent, observed-only odds field readers.

Never fetch another source, infer prices from results, use the race start as the
quote timestamp, manufacture odds or use wager/forecast state.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
import re
from typing import Any

from arvexq.ingest.place_odds import place_odds
from arvexq.v3.data.observed_fields import ensure_circuit

FIELDS = ("win", "place", "popularity", "timestamp", "source", "delta", "missing")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_TIME = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?")
_CIRCUITS = frozenset(("jra", "nar"))


def _runners(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    ensure_circuit(detail, circuit)
    raw = detail.get("horses")
    if not isinstance(raw, list):
        return []
    return [h for h in raw if isinstance(h, dict)]


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() in ("", "-", "--", "不明"))


def _win_value(value: Any) -> bool:
    if isinstance(value, bool) or _blank(value):
        return False
    try:
        return isfinite(float(value)) and float(value) > 0
    except (TypeError, ValueError, OverflowError):
        return False


def _place_value(value: Any) -> bool:
    if isinstance(value, bool) or _blank(value):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return isfinite(float(value)) and value > 0
    return isinstance(value, str) and place_odds(value) is not None


def _popularity_value(value: Any) -> bool:
    if isinstance(value, bool) or _blank(value):
        return False
    if isinstance(value, int):
        return value > 0
    if isinstance(value, str):
        return bool(re.fullmatch(r"[1-9]\d*", value.strip()))
    return False


def _delta_value(value: Any) -> bool:
    if isinstance(value, bool) or _blank(value):
        return False
    try:
        return isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _status(value: Any, validator) -> str:
    return "missing" if _blank(value) else "observed" if validator(value) else "invalid"


def runner_field(detail: dict[str, Any], circuit: str, field: str) -> list[dict[str, Any]]:
    """One factual value per runner; preserve unmodified raw values.

    A zero, NaN, negative price or malformed popularity is not a valid quote.
    A previously computed delta is stored evidence, not recreated here.
    """
    if field not in ("win", "place", "popularity", "delta"):
        raise ValueError("unsupported odds field")
    getters = {
        "win": ("winOdds", _win_value),
        "place": ("placeOdds", _place_value),
        "popularity": ("popularity", _popularity_value),
        "delta": ("observedWinOddsDelta", _delta_value),
    }
    key, validator = getters[field]
    rows = _runners(detail, circuit)
    return [{
        "horseNumber": deepcopy(h.get("horseNumber")),
        "state": _status(h.get(key), validator),
        # Invalid source input does not silently become valid output.
        "value": deepcopy(h.get(key)) if validator(h.get(key)) else None,
    } for h in rows]


def market_field(detail: dict[str, Any], circuit: str, field: str) -> dict[str, Any]:
    """Collect source labels/time only when explicitly present in saved fact.

    HH:MM:SS cannot establish the calendar date or the pre-off quote instant.
    """
    ensure_circuit(detail, circuit)
    if field == "source":
        labels = {key: deepcopy(detail[key]) for key in ("oddsSource", "oddsType")
                  if isinstance(detail.get(key), str) and detail[key].strip()}
        return {
            "state": "observed" if labels else "missing",
            "source": "existing-snapshot-only",
            "labels": labels,
            "independentlyConfirmed": False,
        }
    if field == "timestamp":
        value = detail.get("oddsUpdatedAt")
        if _blank(value):
            return {"state": "missing", "value": None,
                    "precision": "unknown", "preOffTimeVerified": False}
        if isinstance(value, str) and _TIME.fullmatch(value.strip()):
            return {"state": "observed", "value": value.strip(),
                    "precision": "local-time-of-day-only", "preOffTimeVerified": False}
        if isinstance(value, str):
            try:
                timestamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
                if timestamp.tzinfo is not None:
                    return {"state": "observed", "value": value.strip(),
                            "precision": "offset-aware-instant", "preOffTimeVerified": False}
            except ValueError:
                pass
        return {"state": "invalid", "value": None,
                "precision": "unknown", "preOffTimeVerified": False}
    raise ValueError("unsupported market field")


def missing_status(detail: dict[str, Any], circuit: str) -> list[dict[str, Any]]:
    """Independent per-runner absence record, not a model's confidence score."""
    win = runner_field(detail, circuit, "win")
    place = runner_field(detail, circuit, "place")
    rank = runner_field(detail, circuit, "popularity")
    return [{
        "horseNumber": w["horseNumber"],
        "win": w["state"],
        "place": p["state"],
        "popularity": r["state"],
        "atLeastOneObserved": any(x["state"] == "observed" for x in (w, p, r)),
    } for w, p, r in zip(win, place, rank)]
