#!/usr/bin/env python3
"""Licensed BOAT feed -> existing one-day verified JSON publisher.

This is the sole intake to /sports/boat-data/<date>.json. It cannot scrape
BOATRACE or invent entrants, odds, or results. A configured commercial license
and reviewed normalized source are mandatory.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.arvexq_boat_publish import validate_day

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "arvexq/ui/static/sports/boat-data"
MAX_BYTES = 15_000_000


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Licensed feed must not redirect to an unreviewed endpoint")


def fetch_licensed_day(template: str, day: str, token: str) -> dict:
    if template.count("{date}") != 1:
        raise ValueError("Licensed provider URL must include exactly one {date} placeholder")
    url = template.replace("{date}", urllib.parse.quote(day, safe=""))
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Licensed feed must use a reviewed public HTTPS endpoint")
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "ARVEXQ-Licensed-Boat-Feed/1",
        **({"Authorization": "Bearer " + token} if token else {}),
    })
    with urllib.request.build_opener(RejectRedirect()).open(req, timeout=30) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_BYTES:
            raise ValueError("Day file exceeds permitted size")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Day file exceeds permitted size")
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Licensed feed did not return JSON")
    return json.loads(raw.decode("utf-8"))


def merge_public(current: dict | None, incoming: dict) -> dict:
    """Keep previously approved pre-off forecast and official confirmed result."""
    if not current:
        return incoming
    if (current.get("version") != incoming.get("version") or
            current.get("date") != incoming.get("date") or
            current.get("provenanceId") != incoming.get("provenanceId")):
        raise ValueError("Published date, provider or schema changed")
    existing = {str(x["id"]): x for x in current.get("races") or [] if isinstance(x, dict) and x.get("id")}
    merged = dict(existing)
    for r in incoming["races"]:
        old = existing.get(r["id"])
        if not old:
            merged[r["id"]] = r
            continue
        newer = dict(old)
        newer.update(r)
        for key in ("forecast", "selection"):
            if old.get(key):
                if r.get(key) and r[key] != old[key]:
                    raise ValueError("Immutable pre-off " + key + " changed for " + r["id"])
                newer[key] = old[key]
        if old.get("result", {}).get("status") == "confirmed":
            if r.get("result", {}).get("status") == "confirmed" and r["result"] != old["result"]:
                raise ValueError("Confirmed official result changed for " + r["id"])
            newer["result"] = old["result"]
        if old.get("odds3t", {}).get("updatedAt") and not r.get("odds3t"):
            newer["odds3t"] = old["odds3t"]
        if old.get("entries") and not r.get("entries"):
            newer["entries"] = old["entries"]
        merged[r["id"]] = newer
    result = dict(incoming)
    result["races"] = sorted(merged.values(), key=lambda x: (x["venue"], x["raceNo"]))
    result["verifiedAt"] = max(str(current.get("verifiedAt") or ""), str(incoming["verifiedAt"]))
    return result


def ingest(obj: dict, day: str, output: Path = OUTPUT) -> tuple[Path, bool]:
    safe = validate_day(obj)  # enforces explicit commercial rights and real records
    if safe["date"] != day:
        raise ValueError("Licensed feed returned the wrong race date")
    output.mkdir(parents=True, exist_ok=True)
    dest = output / (day + ".json")
    old = json.loads(dest.read_text(encoding="utf-8")) if dest.is_file() else None
    merged = merge_public(old, safe)
    # Reject malformed updates before replacing the public artifact.
    if any(not r.get("id") or not isinstance(r.get("raceNo"), int)
           for r in merged["races"]):
        raise ValueError("Unverified published race identity")
    old_semantic = json.dumps(old, ensure_ascii=False, sort_keys=True) if old else None
    new_semantic = json.dumps(merged, ensure_ascii=False, sort_keys=True)
    if new_semantic == old_semantic:
        return dest, False
    fd, temp = tempfile.mkstemp(dir=output, prefix=".boat-audit-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(merged, fp, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            fp.write("\n")
        os.replace(temp, dest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return dest, True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d"))
    p.add_argument("--input-file", type=Path, help="Reviewed licensed-day file for local testing")
    args = p.parse_args()
    datetime.strptime(args.date, "%Y-%m-%d")
    if args.input_file:
        obj = json.loads(args.input_file.read_text(encoding="utf-8"))
    else:
        template = os.environ.get("ARVEXQ_BOAT_LICENSED_FEED_URL", "")
        if not template:
            raise SystemExit("BOAT_LICENSED_FEED_MISSING: authorized HTTPS day URL must be configured")
        obj = fetch_licensed_day(template, args.date, os.environ.get("ARVEXQ_BOAT_FEED_TOKEN", ""))
    path, updated = ingest(obj, args.date)
    print("BOAT_LICENSED_DAY", "date=", args.date, "races=",
          len(json.loads(path.read_text(encoding="utf-8"))["races"]),
          "updated=", updated, "path=", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
