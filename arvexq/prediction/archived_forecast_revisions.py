"""Read-only retention of *historical* revision receipts after retiring candidate forecasts.

This module does not create revisions, compute scores, or activate any prediction.
Existing append-only revision evidence is retained across D1 syncs.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

VERSION = "arvexq-forecast-revision-v1"


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _valid_current(detail):
    revisions = detail.get("forecastRevisions") or []
    current = detail.get("currentForecastRevisionId")
    if not current:
        return True
    if not isinstance(revisions, list):
        return False
    matches = [revision for revision in revisions
               if isinstance(revision, dict)
               and revision.get("revisionId") == current
               and revision.get("version") == VERSION
               and revision.get("raceId") == detail.get("id")
               and revision.get("raceDate") == detail.get("date")]
    if len(matches) != 1:
        return False
    revision = matches[0]
    return _digest({key: value for key, value in revision.items()
                    if key not in ("revisionId", "createdAt")}) == current


def preserve_archived_revisions(previous, incoming):
    """Preserve the exact old prefix, validate any pointer, never recalculate it."""
    if not isinstance(previous, dict) or not isinstance(incoming, dict):
        raise ValueError("revision retention requires full race dictionaries")
    if previous.get("id") and incoming.get("id") != previous.get("id"):
        raise ValueError("forecast revision owner race mismatch")
    if previous.get("date") and incoming.get("date") != previous.get("date"):
        raise ValueError("forecast revision owner date mismatch")
    out = deepcopy(incoming)
    old = previous.get("forecastRevisions") or []
    proposed = out.get("forecastRevisions") or []
    if not isinstance(old, list) or not isinstance(proposed, list):
        raise ValueError("forecast revision history must be a list")
    if proposed[:len(old)] != old:
        if proposed:
            raise ValueError("forecast revision history prefix changed")
        # Missing history in a thin market update may be restored, but an
        # explicit different pointer is tampering, not an omitted field.
        incoming_pointer = out.get("currentForecastRevisionId")
        original_pointer = previous.get("currentForecastRevisionId")
        if incoming_pointer and incoming_pointer != original_pointer:
            raise ValueError("current forecast revision pointer is invalid")
        out["forecastRevisions"] = deepcopy(old)
        if original_pointer:
            out["currentForecastRevisionId"] = original_pointer
    if out.get("currentForecastRevisionId") and not _valid_current(out):
        raise ValueError("current forecast revision pointer is invalid")
    return out
