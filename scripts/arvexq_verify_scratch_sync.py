#!/usr/bin/env python3
"""Verify that NAR official scratch status reached the production D1 edge.

The complete day is not reloaded. Only races explicitly present in the NAR
official 変更情報 audit are fetched, independently, with bounded retries.
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


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "ARVEXQ-Scratch-Consistency/1",
                      "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def status_in_response(body: Any, number: int) -> bool:
    if not isinstance(body, dict):
        return False
    detail = body.get("detail") or body.get("race") or {}
    fields: list[Any] = [
        body.get("odds"), body.get("odds_current"), body.get("horses"),
        (detail or {}).get("horses") if isinstance(detail, dict) else None,
    ]
    for horses in fields:
        if not isinstance(horses, list):
            continue
        for horse in horses:
            if not isinstance(horse, dict):
                continue
            try:
                no = int(horse.get("horseNumber") or horse.get("horse_no") or 0)
            except (TypeError, ValueError):
                continue
            if no != number:
                continue
            status = str(horse.get("horse_status") or horse.get("status") or "")
            if any(token in status for token in ("取消", "除外", "欠場")) or (
                horse.get("scratched") is True or horse.get("withdrawn") is True
            ):
                return True
    return False


def verify_one(base: str, race_id: str, no: int) -> tuple[str, int, bool, str]:
    error = ""
    for attempt in range(4):
        stamp = int(time.time() * 1000)
        race = urllib.parse.quote(race_id, safe="")
        for endpoint in ("race", "odds"):
            try:
                body = fetch_json(f"{base}/api/{endpoint}/{race}?t={stamp}")
                if status_in_response(body, no):
                    return race_id, no, True, ""
            except Exception as exc:
                error = f"{endpoint}: {type(exc).__name__}: {exc}"
        if attempt < 3:
            time.sleep(attempt + 2)
    return race_id, no, False, error or "withdrawal not present in race or odds endpoint"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", default="live-audit.json")
    parser.add_argument("--api-base", required=True)
    args = parser.parse_args()
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    official = audit.get("official_cancellations") or {}
    requested = [(str(rid), int(no))
                 for rid, horses in official.items()
                 if isinstance(horses, dict)
                 for no in horses]
    print("OFFICIAL_SCRATCH_VERIFY", "official_targets=", len(requested),
          "affected_races=", len(official))
    if not requested:
        print("OFFICIAL_SCRATCH_VERIFY_EMPTY no reported changes on this sync")
        return 0
    errors = []
    with ThreadPoolExecutor(max_workers=min(4, len(requested))) as pool:
        futures = [pool.submit(verify_one, args.api_base.rstrip("/"), rid, no)
                   for rid, no in requested]
        for future in as_completed(futures):
            rid, no, ok, detail = future.result()
            print("OFFICIAL_SCRATCH_D1", rid, "horse=", no,
                  "status=", "OK" if ok else "MISSING", detail)
            if not ok:
                errors.append(f"{rid} horse={no}: {detail}")
    if errors:
        raise SystemExit("SCRATCH_SYNC_NOT_VISIBLE " + "; ".join(errors))
    print("OFFICIAL_SCRATCH_D1_ALL_VISIBLE", len(requested))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
