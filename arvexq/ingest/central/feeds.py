"""central/feeds: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.normalize.central_feed import normalize_central_race
from arvexq.normalize.scalars import _clean
import json
import os
import urllib.parse
import urllib.request


def fetch_central_feed(iso_date: str, history: bool=False, *, fetch_jra_official) -> list[dict]:
    base = _clean(os.getenv("CENTRAL_HISTORY_FEED_URL", "")) if history else ""
    if not base:
        base = _clean(os.getenv("CENTRAL_FEED_URL", ""))
    if not base:
        # JRA official fallback is intended for current/near-current racecards.
        return fetch_jra_official(iso_date)
    if "{date}" in base:
        url = base.replace("{date}", iso_date)
    else:
        url = base + ("&" if "?" in base else "?") + "date=" + iso_date
    headers = {"User-Agent": "KeibaPredictor/6.2", "Accept": "application/json"}
    token = _clean(os.getenv("CENTRAL_HISTORY_FEED_TOKEN", "")) if history else ""
    if not token:
        token = _clean(os.getenv("CENTRAL_FEED_TOKEN", ""))
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=float(os.getenv("CENTRAL_FEED_TIMEOUT_SEC", "12"))) as response:
        body = json.loads(response.read().decode("utf-8"))
    rows = body if isinstance(body, list) else body.get("races", [])
    return [r for r in (normalize_central_race(x) for x in rows) if r]
