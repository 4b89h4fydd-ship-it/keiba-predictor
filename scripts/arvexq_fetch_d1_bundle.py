#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch an ARVEXQ D1 day without using the oversized details=1 endpoint.

The day summary endpoint is small and reliable. Rich race details are fetched
race-by-race so Cloudflare never has to build or return a 40+ MB response.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


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
            return item
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
    args = p.parse_args()

    base = args.api_base.rstrip("/")
    day_url = f"{base}/api/day?date={urllib.parse.quote(args.date)}&details=0&t={int(time.time())}"
    day = get_json(day_url, args.timeout, args.retries)
    races = [r for r in (day.get("races") or []) if isinstance(r, dict) and r.get("id")]
    if not races:
        raise SystemExit(f"D1 returned no races for {args.date}")

    ids = [str(r["id"]) for r in races]
    details_by_id: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    def fetch_one(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        url = f"{base}/api/race/{urllib.parse.quote(rid, safe='')}?t={int(time.time() * 1000)}"
        try:
            value = get_json(url, args.timeout, args.retries)
            detail = detail_from_response(value, rid)
            if detail is None:
                return rid, None, "race endpoint returned no matching detail"
            return rid, detail, ""
        except Exception as exc:
            return rid, None, f"{type(exc).__name__}: {exc}"

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
