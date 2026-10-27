"""Raw data acquisition for the rewrite.

Every fetch returns the exact response bytes plus provenance (URL and
fetch time). Nothing is parsed, repaired or invented here. A response
that is not valid JSON (for example the SPA fallback page served for a
not-yet-generated static file) is reported as unavailable, never as data.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

WEB_BASE = "https://kraizweb1.4b89h4fydd.workers.dev"
API_BASE = "https://kraiz-api.4b89h4fydd.workers.dev"
# The production API rejects non-browser user agents with HTTP 403.
BROWSER_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)

Transport = Callable[[str], bytes]


class SourceUnavailable(RuntimeError):
    """The source did not return usable data (kept distinct from empty data)."""


@dataclass(frozen=True)
class RawPayload:
    kind: str
    source_url: str
    fetched_at: datetime
    body: bytes

    def json(self) -> dict:
        try:
            parsed = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceUnavailable(f"{self.source_url}: not JSON ({exc})") from exc
        if not isinstance(parsed, dict):
            raise SourceUnavailable(f"{self.source_url}: JSON root is not an object")
        return parsed


def http_transport(url: str, timeout: float = 25.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _fetch(kind: str, url: str, transport: Optional[Transport]) -> RawPayload:
    fetch = transport or http_transport
    try:
        body = fetch(url)
    except Exception as exc:  # network / HTTP errors are availability facts
        raise SourceUnavailable(f"{url}: {exc}") from exc
    return RawPayload(
        kind=kind,
        source_url=url,
        fetched_at=datetime.now(timezone.utc),
        body=body,
    )


def fetch_api_races(date: str, transport: Optional[Transport] = None) -> RawPayload:
    """Race summaries for one day: GET /api/races?date=YYYY-MM-DD."""
    url = f"{API_BASE}/api/races?date={urllib.parse.quote(date)}"
    payload = _fetch("api_races", url, transport)
    payload.json()  # fail fast on non-JSON
    return payload


def fetch_api_race_detail(race_id: str, transport: Optional[Transport] = None) -> RawPayload:
    """Full race detail: GET /api/race/<race_id>."""
    url = f"{API_BASE}/api/race/{urllib.parse.quote(race_id, safe='')}"
    payload = _fetch("api_race_detail", url, transport)
    payload.json()
    return payload


def fetch_static_racecards(date: str, transport: Optional[Transport] = None) -> RawPayload:
    """Static entry cards: GET /racecards/<date>.json on the web worker."""
    url = f"{WEB_BASE}/racecards/{urllib.parse.quote(date)}.json"
    payload = _fetch("static_racecards", url, transport)
    parsed = payload.json()
    if "races" not in parsed:
        raise SourceUnavailable(f"{url}: JSON without 'races' (not a racecard file)")
    return payload
