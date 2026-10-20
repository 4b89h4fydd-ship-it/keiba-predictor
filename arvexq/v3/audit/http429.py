"""Privacy-bounded evidence for actual observed HTTP 429 responses.

A response header is *not* sufficient to prove the edge, Worker or origin
generated it. Never log authentication, cookie, query-string or raw body text.
"""
from __future__ import annotations

import re
from typing import Any

LIMIT_HEADERS = {
    "retry-after": "retryAfter",
    "cf-ray": "cfRay",
    "server": "server",
    "content-type": "contentType",
    "cf-cache-status": "cfCacheStatus",
}


def describe_429(exc: Any) -> dict:
    if getattr(exc, "code", None) != 429:
        raise ValueError("observed 429 HTTP response required")
    out = {
        "httpStatus": 429,
        "attribution": "unknown-requires-cloudflare-request-log",
        "responseHeadersObserved": {},
        "responseBodyClass": "unknown",
    }
    headers = getattr(exc, "headers", None)
    if headers is not None:
        for key, friendly in LIMIT_HEADERS.items():
            try:
                value = headers.get(key)
            except (TypeError, AttributeError):
                value = None
            if isinstance(value, str) and len(value) <= 160 and re.fullmatch(r"[A-Za-z0-9 ;,./:_=+\\-]+", value):
                out["responseHeadersObserved"][friendly] = value
    read = getattr(exc, "read", None)
    if callable(read):
        try:
            raw = read(768)
            body = raw.decode("utf-8", errors="ignore").lower() if isinstance(raw, bytes) else ""
            if "1027" in body:
                out["responseBodyClass"] = "cloudflare-worker-free-limit-1027-marker"
            elif "too many requests" in body:
                out["responseBodyClass"] = "too-many-requests-marker"
            elif "<html" in body or "<!doctype" in body:
                out["responseBodyClass"] = "html-error-without-distinct-marker"
            elif body:
                out["responseBodyClass"] = "other-nonempty-body"
            else:
                out["responseBodyClass"] = "empty"
        except (OSError, ValueError, UnicodeError):
            out["responseBodyClass"] = "unreadable"
    return out
