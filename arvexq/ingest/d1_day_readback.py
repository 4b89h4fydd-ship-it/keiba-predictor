"""Read-only day hydration through existing D1 summary and race API routes."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from arvexq.ingest.full_snapshot_codec import KEY as PACKED_DETAIL_KEY, unpack_detail
from arvexq.ingest.career_transport import recover_horse
from arvexq.ingest.full_career import merge_career

MAX_RESPONSE_BYTES = 32 * 1024 * 1024


def get_json(url, *, timeout=20, attempts=2, opener=urllib.request.urlopen,
             sleeper=time.sleep):
    """Bounded GET retries; invalid JSON and schema are not successful reads."""
    if timeout <= 0 or attempts < 1:
        raise ValueError("positive HTTP timeout and attempt count required")
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={
                "accept": "application/json", "user-agent": "ARVEXQ-FactReadback/1"})
            with opener(request, timeout=timeout) as response:
                chunks = []
                total = 0
                # A short read is not EOF; finish this SAME response within
                # the original 32 MiB cap before attempting JSON decode.
                while total <= MAX_RESPONSE_BYTES:
                    chunk = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    chunks.append(chunk)
                raw = b"".join(chunks)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("D1 JSON response exceeds read budget")
            result = json.loads(raw.decode("utf-8"))
            if not isinstance(result, dict):
                raise ValueError("D1 JSON response must be an object")
            return result
        except urllib.error.HTTPError as exc:
            # 429 is a rate-limit signal, never a reason to intensify requests.
            if exc.code == 429 or exc.code not in (408, 500, 502, 503, 504) or attempt + 1 == attempts:
                raise
        except (json.JSONDecodeError, UnicodeDecodeError, http.client.IncompleteRead, OSError):
            # Edge truncation is retried on exactly the original URL, never
            # interpreted as missing horses or an empty D1 original.
            if attempt + 1 == attempts:
                raise
        sleeper(min(2, 0.5 * (attempt + 1)))


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


def _display_parity(full, displayed, day, full_updated, display_updated):
    """Compare persisted facts with the exact existing endpoint read by the PWA.

    Live odds and in-flight result updates are deliberately not compared when
    the underlying saved-detail timestamps differ.
    """
    differences = []
    for key in ("id", "date", "circuit", "track", "raceNumber", "fieldSize"):
        if full.get(key) != displayed.get(key):
            differences.append(key)
    def roster(detail):
        rows = []
        for horse in detail.get("horses") or []:
            if not isinstance(horse, dict):
                raise ValueError("horse is not an object")
            recovered = recover_horse(horse, day)
            past = merge_career(recovered.get("allPastRuns"),
                                recovered.get("recentRaces"), day)
            rows.append((str(horse.get("horseNumber") or ""),
                         str(horse.get("name") or ""),
                         json.dumps(past, ensure_ascii=False, sort_keys=True,
                                    default=str)))
        return sorted(rows)
    if roster(full) != roster(displayed):
        differences.append("horses_or_prior_runs")
    if full_updated is not None and display_updated is not None and str(full_updated) == str(display_updated):
        for key in ("finishers", "payouts"):
            if (full.get("result") or {}).get(key) != (displayed.get("result") or {}).get(key):
                differences.append("result." + key)
    return differences


def read_day(base, day, *, fetch=get_json, workers=3, verify_display=False):
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
        detail = restore_race_response(body, race_id, day)
        updated = body.get("detail_updated_at")
        mismatches = []
        if verify_display:
            if source == "display":
                mismatches.append({"raceId": race_id, "reason": "full_route_unavailable"})
            else:
                try:
                    display_body = fetch(url + "?view=display")
                    raw_display = display_body.get("detail")
                    if isinstance(raw_display, dict) and PACKED_DETAIL_KEY in raw_display:
                        # The PWA consumes body.detail directly; it does not
                        # unpack Python's internal compressed archive format.
                        mismatches.append({"raceId": race_id, "reason": "display_packed_payload_unrenderable"})
                    else:
                        display_detail = restore_race_response(display_body, race_id, day)
                        differences = _display_parity(detail, display_detail, day,
                                                      updated, display_body.get("detail_updated_at"))
                        if differences:
                            mismatches.append({"raceId": race_id, "reason": "display_fact_mismatch",
                                               "fields": differences,
                                               "fullUpdatedAt": updated,
                                               "displayUpdatedAt": display_body.get("detail_updated_at")})
                except Exception as exc:
                    mismatches.append({"raceId": race_id, "reason": "display_read_failed",
                                       "error": type(exc).__name__ + ": " + str(exc)[:240]})
        return detail, source, updated, mismatches

    details, sources, errors, timestamps, parity_errors = {}, {}, {}, {}, {}
    if ids:
        with ThreadPoolExecutor(max_workers=min(workers, 4, len(ids))) as pool:
            futures = {pool.submit(one, race_id): race_id for race_id in ids}
            for future in as_completed(futures):
                race_id = futures[future]
                try:
                    detail, source, updated, mismatches = future.result()
                    details[race_id], sources[race_id] = detail, source
                    timestamps[race_id] = updated
                    if mismatches:
                        parity_errors[race_id] = mismatches
                except Exception as exc:
                    errors[race_id] = {"raceId": race_id,
                        "error": type(exc).__name__ + ": " + str(exc)[:240]}
    return {"date": day, "races": races,
            "details": [details[race_id] for race_id in ids if race_id in details],
            "readbackSources": sources,
            "detailUpdatedAt": timestamps,
            "displayParityErrors": [issue for race_id in ids for issue in parity_errors.get(race_id, [])],
            "readErrors": [errors[race_id] for race_id in ids if race_id in errors]}
