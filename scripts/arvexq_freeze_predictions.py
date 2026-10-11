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
import subprocess
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from arvexq.prediction.prerace_archive import JST, post_at, sealed_lock, seal_detail
from scripts.arvexq_prerace_bet_integrity import has_valid_original, record_failed_attempt


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
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        return {"status": "already-sealed" if sealed_lock(detail) else "started-no-new-lock"}
    existing = sealed_lock(detail)
    if existing:
        if has_valid_original(detail.get("preRaceBet"),
                              race_id=str(detail.get("id") or ""), start_at=post):
            return {"status": "already-sealed", "detail": detail}
        # A previous valid snapshot may precede this feature; preserve its
        # original opinions, and capture a ticket only while still pre-off.
        return {"status": "sealed", "detail": copy.deepcopy(detail),
                "revision": existing.get("sealRevision")}
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
        # Rank ONLY active starters. Ranking a complete roster first silently
        # lets a cancelled runner consume ◎/○ and distort every other mark.
        # Keep the full original roster for the racecard and result collectors.
        working = copy.deepcopy(detail)
        starters = copy.deepcopy(active)
        core_input = copy.deepcopy(working)
        core_input["horses"] = starters
        ranked = assign(core_input)
        if not isinstance(ranked, dict):
            return {"status": "incomplete-prediction"}
        if ranked.get("predictionStatus") == "waiting-for-full-career":
            career = ranked.get("careerReadiness") or {}
            return {
                "status": "waiting-for-full-career",
                "completeHorses": int(career.get("completeHorses") or 0),
                "activeHorses": int(career.get("activeHorses") or len(active)),
                "blockedHorses": list(career.get("blockedHorses") or [])[:8],
            }
        ranked_horses = {
            int(h.get("horseNumber") or 0): h
            for h in (ranked.get("horses") or [])
            if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
        }
        for horse in (working.get("horses") or []):
            no = int(horse.get("horseNumber") or 0)
            if no in ranked_horses:
                evaluated = ranked_horses[no].get("integratedEvaluation")
                if not isinstance(evaluated, dict):
                    return {"status": "no-evaluation"}
                horse["integratedEvaluation"] = copy.deepcopy(evaluated)
            elif no > 0:
                old = dict(horse.get("integratedEvaluation") or {})
                old["mark"] = ""
                horse["integratedEvaluation"] = old
        for key in ("honmeiDecision", "factorRanking", "markEngineVersion",
                    "predictionModelVersion", "winConfidenceEvidence"):
            if key in ranked:
                working[key] = copy.deepcopy(ranked[key])
        lock = build(working)
        if isinstance(lock, dict):
            # Preserve the morning's original marks. Only an authenticated
            # official-condition change may supply a later pre-off revision.
            from arvexq.prediction.official_course_revision import latest_pre_off_marks
            marked = latest_pre_off_marks(detail)
            if marked:
                marked_by_no = {int(z["horseNumber"]): str(z.get("mark") or "")
                                for z in marked["horses"] if isinstance(z, dict)}
                for entry in lock.get("horses") or []:
                    no = int(entry.get("horseNumber") or 0)
                    if no in marked_by_no:
                        entry["mark"] = marked_by_no[no]
                lock["markSource"] = marked.get("version")
                lock["markFixedAt"] = marked.get("revisedAt") or marked.get("fixedAt")
                if marked.get("reason"):
                    lock["markRevisionReason"] = marked["reason"]
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


def capture_original_bet(detail: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Execute the actual client betting core before the off, never on results."""
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        raise ValueError("refusing post-off ticket generation")
    command = ["node", "scripts/arvexq_capture_prerace_bet.js"]
    process = subprocess.run(
        command, input=json.dumps(detail, ensure_ascii=False),
        text=True, capture_output=True, timeout=22,
        env={**os.environ, "TZ": "Asia/Tokyo"},
    )
    if process.returncode:
        raise RuntimeError("bet capture failed: " + process.stderr[-900:])
    result = json.loads(process.stdout.strip())
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        raise ValueError("bet capture returned no ticket model")
    result["raceId"] = str(detail["id"])
    result["fixedAt"] = now.isoformat(timespec="seconds")
    result["fixedBeforePost"] = True
    result["fixedMinutesBeforePost"] = int((post - now).total_seconds() // 60)
    result["lockPolicy"] = "server-js-ticket-v1-no-post-hoc"
    return result


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
    recently_started = []
    for r in races:
        post = post_at(r)
        if not post:
            continue
        minutes = (post - now).total_seconds() / 60
        if 0 < minutes <= max(5, args.ahead_minutes):
            due.append(r)
        elif -20 <= minutes <= 0:
            recently_started.append(r)
    due.sort(key=lambda r: (str(r.get("startTime") or ""), str(r.get("id") or "")))
    report: dict[str, Any] = {
        "version": "v2", "at": now.isoformat(timespec="seconds"), "day": day,
        "races_seen": len(races), "due_count": len(due),
        "sealed": [], "already_sealed": [], "missing": [],
        "missed_after_post": [], "missed_bet_after_post": [],
        "urgent_missing": [], "errors": [],
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
            if datetime.now(JST) >= post_at(detail):
                return {"id": rid, "status": "started-no-new-lock"}
            previous_bet = detail.get("preRaceBet")
            failed_capture = False
            try:
                original = capture_original_bet(detail, now=datetime.now(JST))
                if not has_valid_original(original, race_id=rid, start_at=post_at(detail)):
                    raise ValueError("betting engine returned an invalid or late original")
                detail["preRaceBet"] = original
                if isinstance(previous_bet, dict) and previous_bet.get("captureStatus") == "failed":
                    record_failed_attempt(detail, previous_bet,
                        message=str(previous_bet.get("captureError") or "prior capture failure"),
                        fixed_at=str(previous_bet.get("fixedAt") or ""))
            except Exception as exc:
                failed_capture = True
                detail["preRaceBet"] = record_failed_attempt(
                    detail, previous_bet, message=f"{type(exc).__name__}: {exc}",
                    fixed_at=datetime.now(JST).isoformat(timespec="seconds"))
            if datetime.now(JST) >= post_at(detail):
                return {"id": rid, "status": "started-no-new-lock"}
            payload = {
                "summaries": [], "details": [detail],
                "meta": {"source": "github-actions-prerace-seal-v1",
                         "sync_date": day, "sealed_forecast": True},
            }
            request_json(base + "/api/sync", payload=payload, token=token, retries=4)
            verified = detail_from(request_json(url + "?verify=" + str(time.time_ns())), rid)
            stamp = (verified or {}).get("preRacePrediction") or {}
            bet = (verified or {}).get("preRaceBet") or {}
            if stamp.get("sealRevision") != result["revision"] or not sealed_lock(verified or {}):
                return {"id": rid, "status": "verification-failed"}
            if failed_capture or not has_valid_original(bet, race_id=rid, start_at=post_at(detail)):
                return {"id": rid, "status": "bet-capture-failed",
                        "reason": str(bet.get("captureError") or "no valid original in D1")[:250]}
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
    # Fail visibly for a race that passed the post without a genuine archive.
    # Never retroactively fill the gap, even if the official result is known.
    for row in recently_started:
        rid = str(row["id"])
        try:
            body = request_json(base + "/api/race/" + urllib.parse.quote(rid, safe="")
                                + "?audit=" + str(time.time_ns()))
            d = detail_from(body, rid)
            if not d or not sealed_lock(d):
                report["missed_after_post"].append(rid)
            elif not has_valid_original(d.get("preRaceBet"), race_id=rid, start_at=post_at(d)):
                report["missed_bet_after_post"].append(rid)
        except Exception as exc:
            report["errors"].append({"id": rid, "status": "audit-read-error",
                                     "error": f"{type(exc).__name__}: {exc}"})
    for item in report["missing"]:
        match = next((r for r in due if str(r["id"]) == item["id"]), None)
        post = post_at(match) if match else None
        if post and (post - datetime.now(JST)).total_seconds() <= 7*60:
            report["urgent_missing"].append(item)
    Path(args.audit).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PRERACE_SEAL_AUDIT", json.dumps({
        k: report[k] for k in ("races_seen", "due_count", "sealed", "already_sealed", "missing", "urgent_missing", "missed_after_post", "missed_bet_after_post", "errors")
    }, ensure_ascii=False))
    if report["errors"] or report["urgent_missing"] or report["missed_after_post"] or report["missed_bet_after_post"]:
        return 2
    # Missing race models are logged, not invented; an audit remains available.
    # A completely empty day during scheduled racing signals a failed discovery.
    if not races and 8 <= now.hour <= 23:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
