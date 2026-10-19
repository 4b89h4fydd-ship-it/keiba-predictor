"""Read-only day hydration through existing D1 summary and race API routes."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from arvexq.ingest.full_snapshot_codec import unpack_detail
from arvexq.v3.audit.http429 import describe_429

MAX_RESPONSE_BYTES = 32 * 1024 * 1024

from arvexq.components.item_160.readback_retry import get_json

def restore_race_response(body, race_id, day):
    if not isinstance(body, dict) or body.get("ok") is False:
        raise ValueError("race API did not return a successful object")
    for candidate in (body.get("detail"), body.get("race"), body):
        if isinstance(candidate, dict) and str(candidate.get("id") or "") == race_id:
            detail = unpack_detail(candidate)
            if not isinstance(detail, dict) or str(detail.get("id") or "") != race_id:
                raise ValueError("restored race identity mismatch")
            if str(detail.get("date") or "") != day:
                raise ValueError("race date mismatch")
            return detail
    raise ValueError("race response identity mismatch")


def read_day(base, day, *, fetch=get_json, workers=3):
    """Return facts plus explicit read errors; never request oversized details=1."""
    if date.fromisoformat(day).isoformat() != day or workers < 1:
        raise ValueError("canonical date and positive worker count required")
    root = base.rstrip("/")
    overview = fetch(root + "/api/day?" + urllib.parse.urlencode({"date": day, "details": "0"}))
    if not isinstance(overview, dict) or overview.get("ok") is not True:
        raise ValueError("day API did not confirm a successful read")
    if str(overview.get("date") or "") != day or not isinstance(overview.get("races"), list):
        raise ValueError("day response identity/schema mismatch")
    ids, races = [], overview["races"]
    for row in races:
        if not isinstance(row, dict) or not row.get("id"):
            raise ValueError("race summary identity missing")
        ids.append(str(row["id"]))
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate race summary identity")

    def one(race_id):
        url = root + "/api/race/" + urllib.parse.quote(race_id, safe="")
        source = "full"
        try:
            body = fetch(url)
        except urllib.error.HTTPError as exc:
            if exc.code not in (404, 503):
                raise
            body, source = fetch(url + "?view=display"), "display"
        return restore_race_response(body, race_id, day), source

    details, sources, errors = {}, {}, {}
    if ids:
        with ThreadPoolExecutor(max_workers=min(workers, 4, len(ids))) as pool:
            futures = {pool.submit(one, race_id): race_id for race_id in ids}
            for future in as_completed(futures):
                race_id = futures[future]
                try:
                    details[race_id], sources[race_id] = future.result()
                except Exception as exc:
                    entry = {"raceId": race_id,
                        "error": type(exc).__name__ + ": " + str(exc)[:240]}
                    if getattr(exc, "code", None) == 429:
                        entry["error"] = "api-http-429"
                        entry["httpStatus"] = 429
                        entry["rateLimitEvidence"] = describe_429(exc)
                    errors[race_id] = entry
    return {"date": day, "races": races,
            "details": [details[race_id] for race_id in ids if race_id in details],
            "readbackSources": sources,
            "readErrors": [errors[race_id] for race_id in ids if race_id in errors]}
