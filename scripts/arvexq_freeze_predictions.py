#!/usr/bin/env python3
"""JST near-post server/D1 forecast sealer. Strictly pre-off; never backfill.

Cloudflare D1 is read and written through the existing /api/day, /api/race and
token-authenticated /api/sync endpoints. This does not require the app to be open.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from arvexq.prediction.prerace_archive import JST, post_at, sealed_lock, seal_detail


def request_json(url: str, *, payload: dict | None = None, token: str = "", retries: int = 3) -> dict:
    headers = {"accept": "application/json", "user-agent": "ARVEXQ-PreRace-Seal/1"}
    if payload is not None:
        headers["content-type"] = "application/json"
        headers["x-sync-token"] = token
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    error = None
    for attempt in range(max(1, retries)):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
            with urllib.request.urlopen(req, timeout=25) as response:
                b = response.read()
            value = json.loads(b.decode("utf-8")) if b else {}
            if not isinstance(value, dict) or value.get("ok") is False:
                raise ValueError("non-success JSON reply from sync API")
            return value
        except Exception as exc:
            error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {type(error).__name__}: {error}")


def detail_from(body: dict, rid: str) -> dict | None:
    for item in (body.get("detail"), body.get("race"), body):
        if isinstance(item, dict) and str(item.get("id") or "") == rid:
            return item
    return None


def prepare_seal(detail: dict, *, now: datetime, build=None, assign=None) -> dict:
    """Pure testable decision core; does not mutate or publish any race."""
    if sealed_lock(detail):
        return {"status": "already-sealed", "detail": detail}
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        return {"status": "started-no-new-lock"}
    if not isinstance(detail.get("horses"), list):
        return {"status": "missing-roster"}
    active = [h for h in detail["horses"] if isinstance(h, dict)
              and int(h.get("horseNumber") or 0) > 0 and not h.get("scratched")
              and not h.get("withdrawn") and not any(s in str(h.get("status") or "")
              for s in ("取消", "除外", "欠場"))]
    if len(active) < 3 or any(not str(h.get("name") or "").strip() for h in active):
        return {"status": "incomplete-roster"}
    if not any((h.get("recentRaces") or h.get("allPastRuns"))
               for h in active) and detail.get("analysisMode") not in ("新馬", "障害"):
        return {"status": "missing-historical-evidence"}
    if assign is None:
        from arvexq.prediction.final_marks import apply_core_marks
        assign = apply_core_marks
    if build is None:
        import app
        build = app._build_prerace_prediction
    try:
        working = assign(copy.deepcopy(detail))
        lock = build(working)
        if not isinstance(lock, dict) or int(lock.get("markCount") or 0) < 3:
            return {"status": "incomplete-prediction"}
        if sum(1 for h in active if str(h.get("name") or "").strip()) != len(active):
            return {"status": "incomplete-roster"}
        if not any(h.get("integratedEvaluation") for h in working.get("horses") or []):
            return {"status": "no-evaluation"}
        sealed = seal_detail(working, lock, now)
        return {"status": "sealed", "detail": sealed, "revision": sealed["preRacePrediction"]["sealRevision"]}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev"))
    parser.add_argument("--audit", default="prerace-freeze-report.json")
    parser.add_argument("--ahead-minutes", type=int, default=35)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    base = args.api_base.rstrip("/")
    token = os.getenv("SYNC_TOKEN", "")
    if not token:
        raise SystemExit("SYNC_TOKEN not configured — refusing unsigned writes")
    now = datetime.now(JST)
    day = now.date().isoformat()
    day_body = request_json(f"{base}/api/day?date={day}&details=0&t={int(time.time())}")
    races = [r for r in (day_body.get("races") or []) if isinstance(r, dict) and r.get("id")]
    due = []
    for r in races:
        post = post_at(r)
        if not post:
            continue
        minutes = (post - now).total_seconds() / 60
        if 0 < minutes <= max(5, args.ahead_minutes):
            due.append(r)
    due.sort(key=lambda r: (str(r.get("startTime") or ""), str(r.get("id") or "")))
    report: dict[str, Any] = {
        "version": "v1", "at": now.isoformat(timespec="seconds"), "day": day,
        "races_seen": len(races), "due_count": len(due),
        "sealed": [], "already_sealed": [], "missing": [], "errors": [],
    }

    def execute(row: dict) -> dict:
        rid = str(row["id"])
        url = base + "/api/race/" + urllib.parse.quote(rid, safe="")
        try:
            body = request_json(url + "?t=" + str(int(time.time() * 1000)))
            old = detail_from(body, rid)
            if not old:
                return {"id": rid, "status": "missing-detail"}
            result = prepare_seal(old, now=datetime.now(JST))
            if result["status"] != "sealed":
                return {"id": rid, **{k: v for k, v in result.items() if k not in ("detail",)}}
            detail = result["detail"]
            payload = {
                "summaries": [], "details": [detail],
                "meta": {"source": "github-actions-prerace-seal-v1",
                         "sync_date": day, "sealed_forecast": True},
            }
            request_json(base + "/api/sync", payload=payload, token=token, retries=4)
            verified = detail_from(request_json(url + "?verify=" + str(time.time_ns())), rid)
            stamp = (verified or {}).get("preRacePrediction") or {}
            if stamp.get("sealRevision") != result["revision"] or not sealed_lock(verified or {}):
                return {"id": rid, "status": "verification-failed"}
            return {"id": rid, "status": "sealed", "revision": result["revision"]}
        except Exception as exc:
            return {"id": rid, "status": "error", "error": f"{type(exc).__name__}: {exc}"}

    if due:
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 4, len(due)))) as pool:
            futures = [pool.submit(execute, r) for r in due]
            for f in as_completed(futures):
                row = f.result()
                if row["status"] == "sealed":
                    report["sealed"].append(row["id"])
                elif row["status"] == "already-sealed":
                    report["already_sealed"].append(row["id"])
                elif row["status"] in ("error", "verification-failed"):
                    report["errors"].append(row)
                else:
                    report["missing"].append(row)
    Path(args.audit).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PRERACE_SEAL_AUDIT", json.dumps({
        k: report[k] for k in ("races_seen", "due_count", "sealed", "already_sealed", "missing", "errors")
    }, ensure_ascii=False))
    if report["errors"]:
        return 2
    # Missing race models are logged, not invented; an audit remains available.
    # A completely empty day during scheduled racing signals a failed discovery.
    if not races and 8 <= now.hour <= 23:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
