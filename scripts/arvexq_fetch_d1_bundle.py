#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch an ARVEXQ D1 day without using the oversized details=1 endpoint.

The day summary endpoint is small and reliable. Rich race details are fetched
race-by-race so Cloudflare never has to build or return a 40+ MB response.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Direct execution as "python scripts/..." puts scripts/, not repo root,
# on sys.path. The workflow invokes this entrypoint directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.ingest.full_snapshot_codec import KEY as FULL_PAYLOAD_KEY, unpack_detail


def get_json(url: str, timeout: float, retries: int) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "ARVEXQ-D1-Hydrator/1"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("response is not a JSON object")
            return value
        except Exception as exc:  # transient Worker/network failures are retried
            last = exc
            if attempt + 1 < max(1, retries):
                time.sleep(min(5.0, 0.75 * (attempt + 1)))
    raise RuntimeError(f"GET failed after {retries} attempt(s): {url}: {type(last).__name__}: {last}")


def detail_from_response(value: dict[str, Any], rid: str) -> dict[str, Any] | None:
    candidates = [value, value.get("detail"), value.get("race")]
    for item in candidates:
        if isinstance(item, dict) and str(item.get("id") or "") == rid:
            detail = unpack_detail(item) if FULL_PAYLOAD_KEY in item else item
            if str(detail.get("id") or "") != rid:
                raise ValueError("restored full payload race identity mismatch")
            return detail
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-base", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report", default="")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=float, default=25.0)
    p.add_argument("--retries", type=int, default=4)
    p.add_argument("--allow-missing-details", action="store_true")
    p.add_argument("--exclude-retired-banei", action="store_true",
                   help="For flat JRA/NAR research only: omit explicitly retired Banei summaries")
    p.add_argument("--allow-empty-day", action="store_true", help="Accept an explicitly empty D1 day for cold-start publication")
    args = p.parse_args()

    base = args.api_base.rstrip("/")
    day_url = f"{base}/api/day?date={urllib.parse.quote(args.date)}&details=0&t={int(time.time())}"
    day = get_json(day_url, args.timeout, args.retries)
    races = [r for r in (day.get("races") or []) if isinstance(r, dict) and r.get("id")]
    retired = []
    if args.exclude_retired_banei:
        retired = [r for r in races if str(r.get("track") or "") in ("帯広","帯広ば")
                   or "-帯広-" in str(r["id"]) or "-帯広ば-" in str(r["id"])]
        races = [r for r in races if r not in retired]
        if retired:
            print("D1_RETIRED_BANEI_SUMMARIES_IGNORED_FOR_FLAT_REPLAY",
                  len(retired), [r["id"] for r in retired])
    if not races:
        # A newly opened calendar day has no D1 summaries yet. Full Prefetch
        # must publish its locally prepared official race list, not abort here.
        # Network errors / invalid API responses still fail closed.
        if not args.allow_empty_day or not isinstance(day.get("races"), list):
            raise SystemExit(f"D1 returned no races for {args.date}")
        observed_date = str(day.get("date") or "")
        if observed_date and observed_date != args.date:
            raise SystemExit(f"D1 returned mismatched date {observed_date} for {args.date}")
        empty = {"date": args.date, "races": [], "details": []}
        Path(args.out).write_text(json.dumps(empty, ensure_ascii=False), encoding="utf-8")
        report = {"date": args.date, "race_count": 0, "detail_count": 0,
                  "missing_detail_count": 0, "missing_details": [], "empty_day": True}
        if args.report:
            Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("D1_EMPTY_DAY_READY_FOR_INITIAL_PUBLICATION", args.date)
        return 0

    ids = [str(r["id"]) for r in races]
    details_by_id: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    def fetch_one(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        # Two READ views of the same existing D1 race_details table. The
        # original route can return 404 for a record available as the stored
        # display payload. Never accept a different race's response.
        url = f"{base}/api/race/{urllib.parse.quote(rid, safe='')}"
        failures = []
        for suffix in ("?t=", "?view=display&t="):
            candidate = url + suffix + str(int(time.time() * 1000))
            try:
                value = get_json(candidate, args.timeout, args.retries)
                detail = detail_from_response(value, rid)
                if detail is not None:
                    return rid, detail, ""
                failures.append("race endpoint returned no matching detail")
            except Exception as exc:
                failures.append(f"{type(exc).__name__}: {exc}")
        return rid, None, " | ".join(failures)[:450]

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(ids)))) as pool:
        futures = {pool.submit(fetch_one, rid): rid for rid in ids}
        for fut in as_completed(futures):
            rid, detail, error = fut.result()
            if detail is not None:
                details_by_id[rid] = detail
            else:
                errors[rid] = error
                print("D1_DETAIL_FETCH_ERROR", rid, error)

    # The Worker occasionally returns HTTP 503 for a few large cards while
    # a broad 8-worker scan is ongoing. Recover those IDs sequentially rather
    # than declaring the entire day incomplete after the first parallel pass.
    transient = [
        rid for rid in ids if rid in errors
        and any(token in errors[rid] for token in ("HTTP Error 503", "HTTP Error 502", "HTTP Error 429", "timed out"))
    ]
    for rid in transient:
        print("D1_DETAIL_SERIAL_RETRY", rid)
        try:
            _, detail, error = fetch_one(rid)
            if detail is not None:
                details_by_id[rid] = detail
                errors.pop(rid, None)
                print("D1_DETAIL_SERIAL_RECOVERED", rid)
            elif error:
                errors[rid] = error
        except Exception as exc:
            errors[rid] = f"serial retry {type(exc).__name__}: {exc}"

    details = [details_by_id[rid] for rid in ids if rid in details_by_id]
    out = dict(day)
    out["date"] = out.get("date") or args.date
    out["races"] = races
    out["details"] = details
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

    report = {
        "date": args.date,
        "race_count": len(races),
        "detail_count": len(details),
        "retired_banei_excluded_count": len(retired),
        "missing_detail_count": len(errors),
        "missing_details": [{"race_id": rid, "error": errors[rid]} for rid in ids if rid in errors],
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "D1_BUNDLE_AUDIT",
        f"races={len(races)}",
        f"details={len(details)}",
        f"missing={len(errors)}",
    )
    if errors and not args.allow_missing_details:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
