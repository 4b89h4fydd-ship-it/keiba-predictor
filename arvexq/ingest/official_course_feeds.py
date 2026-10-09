"""Poll an explicitly configured authorized official-course data feed.

Requires a feed delivering timestamped facts verifiably sourced from official
racecourse publications. It is not a scraper of winner/order inference.
Without a configured provider no 'official bias update' is claimed.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from arvexq.prediction.official_course_revision import official_event, pre_off_change

def fetch_course_events(date: str, rows: list[dict[str, Any]], *, now: datetime) -> dict[str, dict[str, Any]]:
    api = os.getenv("ARVEXQ_OFFICIAL_COURSE_FEED_URL", "").strip()
    token = os.getenv("ARVEXQ_OFFICIAL_COURSE_FEED_TOKEN", "").strip()
    if not api or not token:
        return {}
    parts = urllib.parse.urlsplit(api)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("official course feed URL must be trusted HTTPS")
    url = api + ("&" if parts.query else "?") + urllib.parse.urlencode({"date": date})
    req = urllib.request.Request(url, headers={
        "accept": "application/json", "authorization": "Bearer " + token,
        "user-agent": "ARVEXQ-OfficialCourse/1",
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        body = json.load(response)
    if not isinstance(body, dict) or not isinstance(body.get("events"), list):
        raise ValueError("official course feed missing events list")
    # Only a bounded set of explicitly cited, official-course observations.
    events = []
    for raw in body["events"][:200]:
        event = official_event(raw)
        if event and event["raceDate"] == date:
            events.append(event)
    result: dict[str, dict[str, Any]] = {}
    for race in rows:
        if not isinstance(race, dict) or not race.get("id"):
            continue
        surface = str(race.get("surface") or "")
        candidates = [e for e in events if
                      e["track"] == str(race.get("track") or "")
                      and (not surface or e["surface"] == surface)]
        if not candidates:
            continue
        candidates.sort(key=lambda x: x["publishedAt"])
        event = candidates[-1]
        if pre_off_change(race, race.get("officialCourseCondition"), event, now):
            result[str(race["id"])] = event
    return result
