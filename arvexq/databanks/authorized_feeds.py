"""Contract-based connections for licensed historical horse-racing datasets.

Nothing in this module scrapes website HTML or assumes permission to republish.
Operators may add any number of separately authorised HTTPS JSON feeds via
ARVEXQ_AUTHORIZED_HISTORY_FEEDS_JSON without changing prediction/UI code.

Format: [{"name":"partner-id","circuit":"JRA|NAR|both",
          "url":"https://licensed-provider.example/api/history",
          "token_env":"ARVEXQ_PARTNER_TOKEN","priority":25,
          "horse_first3f":true,"horse_early_timing":true}]

Request (GET): horseId, horseName, raceDate, limit, circuit.
Response JSON: {"horseId": "...", "horseName": "...",
                "recentRaces":[{"date":"2026-09-01", "track":"大井",
                 "distance":1400,"raceNumber":7,"cornerPositions":[2,2,3,3],
                 "first3FSeconds":36.8,
                 "earlyTiming":{"sourceKind":"individual_sensor",
                 "sourceRef":"provider:sample-record-id",
                 "first200mSeconds":13.4,
                 "gateReactionSeconds":0.32,
                 "acceleration0to100Mps2":2.8},...}],
                "allPastRuns":[...]}
Optional fields must represent actual source observations; never infer a horse's
first 3F from the race's collective first 3F. Historical cutoff is enforced by
the downstream _merge_runs too.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

from .registry import DataBankRegistry, DataSource, SourceCapabilities


CONFIG_ENV = "ARVEXQ_AUTHORIZED_HISTORY_FEEDS_JSON"
_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,63}$")


def _valid_url(url: str) -> str:
    value = (url or "").strip()
    u = urllib.parse.urlsplit(value)
    if (
        u.scheme != "https" or not u.hostname or u.username or u.password or
        u.fragment or u.port not in (None, 443) or u.hostname.lower() in
        {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Authorised history feed URL must use external HTTPS")
    return value


def configured_feeds(config: str | None = None, *, environ: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    env = os.environ if environ is None else environ
    raw = config if config is not None else env.get(CONFIG_ENV, "")
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Authorized history feeds config must be a list")
    result: list[dict[str, Any]] = []
    names: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Authorized history provider must be an object")
        name = str(item.get("name") or "").strip()
        circuit = str(item.get("circuit") or "").strip()
        token_env = str(item.get("token_env") or "").strip()
        if not _NAME.fullmatch(name) or circuit not in {"JRA", "NAR", "both"}:
            raise ValueError("Invalid authorized feed name or circuit")
        if token_env and not re.fullmatch(r"[A-Z][A-Z0-9_]{2,127}", token_env):
            raise ValueError("Token environment variable must be an environment key")
        if name in names:
            raise ValueError("Duplicate authorized history feed name")
        names.add(name)
        endpoint = _valid_url(str(item.get("url") or ""))
        priority = int(item.get("priority", 30))
        if not 1 <= priority <= 1000:
            raise ValueError("Authorized history priority must be between 1 and 1000")
        # Configured endpoint is not necessarily enabled. Require explicit
        # credentials when a provider declares a token_env.
        enabled = not token_env or bool(env.get(token_env, ""))
        result.append({
            "name": name, "circuit": circuit, "url": endpoint,
            "token_env": token_env, "priority": priority, "enabled": enabled,
            "horse_first3f": item.get("horse_first3f") is True,
            "horse_early_timing": item.get("horse_early_timing") is True,
        })
    return result


def _validated_early_timing(data: Any) -> dict[str, Any] | None:
    """Accept licensed horse observations only, never a race leader sectional."""
    if not isinstance(data, dict):
        return None
    kind = str(data.get("sourceKind") or "")
    reference = str(data.get("sourceRef") or "").strip()
    if kind not in {"individual_sensor", "video_estimate"} or not reference:
        return None
    clean: dict[str, Any] = {"sourceKind": kind, "sourceRef": reference[:400]}
    intervals = {
        "first200mSeconds": (7.0, 25.0),
        "gateReactionSeconds": (0.05, 3.0),
        "acceleration0to100Mps2": (0.1, 10.0),
    }
    for key, (minimum, maximum) in intervals.items():
        val = data.get(key)
        if val is None or val == "":
            continue
        try:
            value = float(val)
        except (TypeError, ValueError):
            continue
        if minimum <= value <= maximum:
            clean[key] = value
    if not any(key in clean for key in intervals):
        return None
    return clean


def _request_history(config: dict[str, Any], horse: dict[str, Any], race: dict[str, Any], limit: int) -> dict[str, Any]:
    h_id = str(horse.get("horseId") or horse.get("id") or "").strip()
    h_name = str(horse.get("name") or "").strip()
    date = str(race.get("date") or "").strip()
    if not date or not (h_id or h_name):
        return {}
    qs = urllib.parse.urlencode({
        "horseId": h_id, "horseName": h_name,
        "raceDate": date, "limit": min(5, max(1, int(limit or 5))),
        "circuit": "JRA" if str(race.get("circuit")) in {"JRA", "中央"} else "NAR",
    })
    url = config["url"] + ("&" if "?" in config["url"] else "?") + qs
    headers = {"Accept": "application/json", "User-Agent": "ARVEXQ-authorized-data-client/1.0"}
    token_key = config["token_env"]
    if token_key:
        token = os.environ.get(token_key, "")
        if not token:
            return {}
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=8) as response:
        raw = response.read(1_500_001)
    if len(raw) > 1_500_000:
        raise ValueError("Authorized history response exceeds size limit")
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Authorized history response must be a JSON object")
    received_id = str(obj.get("horseId") or "").strip()
    received_name = str(obj.get("horseName") or "").strip()
    if h_id and received_id and received_id != h_id:
        raise ValueError("Authorized history response horseId mismatch")
    if not h_id and h_name and received_name and received_name != h_name:
        raise ValueError("Authorized history response horseName mismatch")
    out: dict[str, Any] = {}
    for key in ("recentRaces", "allPastRuns"):
        rows = obj.get(key)
        if isinstance(rows, list):
            valid = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                d = str(row.get("date") or row.get("raceDate") or "")
                if d and d < date:
                    item = dict(row)
                    # Only an explicitly declared per-horse measurement can
                    # populate this field. Do not use a race-level opening 3F.
                    if config.get("horse_first3f") and item.get("horseFirst3FSeconds") in (None, ""):
                        value = item.get("first3FSeconds")
                        try:
                            seconds = float(value)
                        except (TypeError, ValueError):
                            seconds = 0.0
                        if 15 <= seconds <= 90:
                            item["horseFirst3FSeconds"] = seconds
                            item["horseEarly3FSource"] = config["name"]
                    # Permit individual timing only from explicitly contracted
                    # horse-level feeds, with nonempty provenance and plausible
                    # numeric bounds. A race's first-1F lap cannot substitute.
                    timing = _validated_early_timing(item.get("earlyTiming")) if config.get("horse_early_timing") else None
                    if timing:
                        item["earlyTiming"] = timing
                    else:
                        item.pop("earlyTiming", None)
                    valid.append(item)
            out[key] = valid
    return out


def register_authorized_history_feeds(
    registry: DataBankRegistry,
    *,
    config: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Register only configured, enabled partners; each fetch fails independently."""
    feeds = configured_feeds(config, environ=environ)
    registered: list[str] = []
    for feed in feeds:
        if not feed["enabled"]:
            continue
        if registry.get(feed["name"]) is not None:
            raise ValueError("Authorized feed name collides with an existing provider")
        # The request handler obtains its token at request time so secret
        # values are never captured in registered closures or source metadata.
        def fetch(horse: dict[str, Any], race: dict[str, Any], limit: int = 5, *, _feed=feed):
            return _request_history(_feed, horse, race, limit)

        registry.register(DataSource(
            name=feed["name"], circuit=feed["circuit"], priority=feed["priority"],
            capabilities=SourceCapabilities(horse_history=True),
            fetchers={"horse_history": fetch},
            supplement_complete_history=feed["horse_first3f"] or feed["horse_early_timing"],
        ))
        registered.append(feed["name"])
    return registered
