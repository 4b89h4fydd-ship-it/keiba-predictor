#!/usr/bin/env python3
"""Fail-closed D1 sync sender: classify permanent failures before any retry.

Capacity limit and Cloudflare Worker 1102 cannot be solved by replaying the same
multi-megabyte request. No deletions, schema changes or prediction rewrites.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PERMANENT_CAPACITY = "storage-capacity-exhausted"
PERMANENT_WORKER_LIMIT = "worker-resource-limit-1102"
PERMANENT_TOO_LARGE = "request-too-large"
PERMANENT_AUTH = "sync-auth-or-permission"
TRANSIENT = "transient-upstream"
UNKNOWN = "unclassified-sync-failure"


def classify(status: int, content: bytes) -> str:
    body = content[:4096].decode("utf-8", "replace").lower()
    if "exceeded maximum db size" in body or "database or disk is full" in body or (
        "d1_error" in body and "maximum" in body and ("db size" in body or "database size" in body)
    ):
        return PERMANENT_CAPACITY
    if "error code: 1102" in body or "worker exceeded resource limits" in body or (
        "error 1102" in body
    ):
        return PERMANENT_WORKER_LIMIT
    if status == 413 or "request entity too large" in body or "request body too large" in body:
        return PERMANENT_TOO_LARGE
    if status in (401, 403):
        return PERMANENT_AUTH
    if status in (429, 500, 502, 503, 504, 408) or status == 0:
        return TRANSIENT
    return UNKNOWN


def post(path: Path, url: str, token: str, *, retries: int = 2,
         max_bytes: int = 4_000_000, timeout: float = 25.0,
         opener=urllib.request.urlopen, sleeper=time.sleep) -> dict:
    size = path.stat().st_size
    if size > max_bytes:
        return {"ok": False, "reason": PERMANENT_TOO_LARGE, "status": 0,
                "attempts": 0, "bytes": size}
    if size == 0:
        return {"ok": False, "reason": UNKNOWN, "status": 0,
                "attempts": 0, "bytes": size}
    body = path.read_bytes()
    # The sync token is NEVER emitted in diagnostics.
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"content-type": "application/json", "x-sync-token": token,
                 "user-agent": "ARVEXQ-CapacityGuard/1"},
    )
    attempts = max(1, retries + 1)
    for attempt in range(attempts):
        status = 0
        message = b""
        try:
            with opener(req, timeout=timeout) as response:
                status = int(response.status)
                message = response.read(4096)
            if 200 <= status < 300:
                # Never treat an HTTP 200 body containing an explicit error as success.
                try:
                    decoded = json.loads(message)
                except (ValueError, UnicodeError):
                    decoded = None
                if isinstance(decoded, dict) and decoded.get("ok") is False:
                    reason = classify(500, message)
                else:
                    return {"ok": True, "reason": "ok", "status": status,
                            "attempts": attempt + 1, "bytes": size}
            else:
                reason = classify(status, message)
        except urllib.error.HTTPError as err:
            status = err.code
            message = err.read(4096)
            reason = classify(status, message)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            reason = TRANSIENT
        if reason != TRANSIENT or attempt + 1 == attempts:
            return {"ok": False, "reason": reason, "status": status,
                    "attempts": attempt + 1, "bytes": size}
        sleeper(min(4.0, 1.5 * (attempt + 1)))
    raise AssertionError("unreachable")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--api-base", required=True)
    p.add_argument("--max-bytes", type=int, default=4_000_000)
    p.add_argument("--retries", type=int, default=2)
    args = p.parse_args()
    token = os.environ.get("SYNC_TOKEN") or ""
    if not token:
        print("D1_SYNC_ABORT reason=missing-sync-token")
        return 2
    try:
        result = post(Path(args.file), args.api_base.rstrip("/") + "/api/sync",
                      token, retries=args.retries, max_bytes=args.max_bytes)
    except Exception as exc:
        # No exception text: could contain headers or a private URL.
        print("D1_SYNC_ABORT reason=internal-error type=" + type(exc).__name__)
        return 2
    print("D1_SYNC_GUARD", "batch=" + Path(args.file).name,
          "bytes=" + str(result["bytes"]),
          "status=" + str(result["status"]),
          "attempts=" + str(result["attempts"]),
          "reason=" + result["reason"])
    if result["ok"]:
        return 0
    if result["reason"] in (PERMANENT_CAPACITY, PERMANENT_WORKER_LIMIT,
                             PERMANENT_TOO_LARGE, PERMANENT_AUTH):
        print("::error::D1_WRITE_BLOCKED_SAFE_NO_DATA_DELETED " + result["reason"])
        return 20
    print("::error::D1_SYNC_NOT_CONFIRMED " + result["reason"])
    return 21


if __name__ == "__main__":
    sys.exit(main())
