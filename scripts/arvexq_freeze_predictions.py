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
    """Decode the persisted full snapshot BEFORE testing the history or seal.

    Full Prefetch packs careers, marks and immutable pre-race evidence inside
    arvexqFullPayload; the top-level horse list is intentionally a thin index.
    Failing to unpack it makes a real history appear completely missing.
    Never trust a corrupt or cross-race envelope.
    """
    from arvexq.ingest.full_snapshot_codec import KEY, unpack_detail
    for item in (body.get("detail"), body.get("race"), body):
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") != rid:
            continue
        result = unpack_detail(item) if KEY in item else item
        if not isinstance(result, dict) or str(result.get("id") or "") != rid:
            raise ValueError("restored D1 race identity mismatch")
        return result
    return None



def fetch_existing_d1_detail(base: str, rid: str, *, now: datetime, reader=None) -> dict | None:
    """Read existing D1 views, never infer/construct historical starts.

    The primary race response may be a slim legacy representation while
    ?view=display exposes the already-stored rich race_details payload.
    Only use the richer view for the same active race and before post.
    """
    if reader is None:
        reader = request_json
    url = base.rstrip("/") + "/api/race/" + urllib.parse.quote(rid, safe="")
    primary = None
    primary_error = None
    try:
        primary = detail_from(reader(url + "?t=" + str(time.time_ns())), rid)
    except Exception as exc:
        primary_error = exc
    if primary is not None and (sealed_lock(primary) or _history_count(primary) > 0):
        return primary
    try:
        display = detail_from(reader(url + "?view=display&t=" + str(time.time_ns())), rid)
    except Exception:
        if primary_error is not None:
            raise primary_error
        return primary
    if display is None:
        return primary
    post = post_at(display)
    if post is None or now.astimezone(JST) >= post:
        return primary
    if primary is not None:
        if str(primary.get("date") or "") != str(display.get("date") or ""):
            raise ValueError("D1 detail display date mismatch")
        def active_numbers(detail):
            return {int(h["horseNumber"]) for h in detail.get("horses") or []
                    if isinstance(h, dict) and type(h.get("horseNumber")) is int
                    and not h.get("scratched") and not h.get("withdrawn")
                    and not any(s in str(h.get("status") or "") for s in ("取消", "除外", "欠場"))}
        a, b = active_numbers(primary), active_numbers(display)
        if a and a != b:
            raise ValueError("D1 detail display active field mismatch")
    # Existing sealed originals are always the source of truth.
    if sealed_lock(display):
        return display
    if _history_count(display) > _history_count(primary):
        return display
    return primary if primary is not None else display


def _history_count(detail: dict | None) -> int:
    if not isinstance(detail, dict):
        return 0
    return sum(len(h.get("allPastRuns") or h.get("recentRaces") or [])
               for h in detail.get("horses") or [] if isinstance(h, dict))


def _active_history_missing(detail: dict | None) -> bool:
    """An individual active runner without a past run also needs the existing rescue."""
    if not isinstance(detail, dict):
        return False
    return any(
        not (h.get("allPastRuns") or h.get("recentRaces"))
        for h in (detail.get("horses") or [])
        if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
        and not h.get("scratched") and not h.get("withdrawn")
        and not any(x in str(h.get("status") or "") for x in ("取消", "除外", "欠場"))
    )


def recover_prior_history_before_post(detail: dict, *, now: datetime, run=None) -> dict:
    """Use the EXISTING registered history sources before off, with a hard timeout.

    Provider enrichment runs in an isolated process and never synthesizes a
    prediction. The helper validates exact race identity, roster and dated runs.
    """
    if not isinstance(detail, dict) or not detail.get("id"):
        raise ValueError("race detail required")
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        raise ValueError("post-off provider rescue forbidden")
    if not _active_history_missing(detail):
        return detail
    if run is None:
        run = subprocess.run
    proc = run(
        [__import__("sys").executable, "scripts/arvexq_preoff_history_rescue.py"],
        input=json.dumps(detail, ensure_ascii=False), text=True,
        capture_output=True, timeout=55,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    if proc.returncode:
        raise RuntimeError("registered history sources returned no verified runs: " +
                           (proc.stderr or "")[-250:])
    recovered = json.loads(proc.stdout)
    if not isinstance(recovered, dict) or recovered.get("id") != detail["id"]:
        raise ValueError("provider rescue race identity mismatch")
    if recovered.get("date") != detail.get("date") or post_at(recovered) != post:
        raise ValueError("provider rescue day or time mismatch")
    if not _history_count(recovered):
        raise ValueError("no real historical observations from registered sources")
    # The subprocess enforces runner identity and pre-race run dates. The
    # orchestration boundary independently confirms that the roster is intact.
    from scripts.arvexq_preoff_history_rescue import active_identity
    if active_identity(detail) != active_identity(recovered):
        raise ValueError("provider rescue active field mismatch")
    if datetime.now(JST) >= post:
        raise ValueError("provider lookup completed after the scheduled post")
    return recovered


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
    # Keep the existing immutable D1 seal. For the approved 2026-10-23+
    # production forecast, consume independently validated fusion rather than Stage64.
    # Explicit test-injected assign/build functions retain their old contract.
    if detail.get("date", "") >= "2026-10-23" and assign is None and build is None:
        from arvexq.forecast.engine import build_prediction
        from arvexq.forecast.marks import generate_marks
        from arvexq.forecast.tickets import generate_tickets
        # Prefetch already computed five actual methods and its empirical
        # weights before the off. The sealer must freeze THAT recorded opinion,
        # not demand a fresh set of models or synthesize a second prediction.
        existing_prediction = detail.get("prediction")
        prediction = None
        if (isinstance(existing_prediction, dict)
                and existing_prediction.get("modelVersion") == "arvexq-empirical-fusion-v1"
                and existing_prediction.get("predictionStatus") == "ready"
                and existing_prediction.get("productionEligible") is True
                and existing_prediction.get("raceId") == detail.get("id")
                and existing_prediction.get("date") == detail.get("date")
                and detail.get("predictionModelVersion") == existing_prediction.get("modelVersion")
                and detail.get("predictionStatus") == "ready"):
            try:
                captured = datetime.fromisoformat(
                    str(existing_prediction["capturedAt"]).replace("Z","+00:00"))
                if captured.tzinfo and captured <= now and captured < post:
                    prediction = copy.deepcopy(existing_prediction)
            except (KeyError, ValueError, TypeError):
                prediction = None
        if prediction is None:
            prediction = build_prediction(detail, now=now)
        if prediction is None:
            return {"status": "incomplete-prediction", "predictionStatus": "disabled"}
        marks = generate_marks(prediction)
        tickets = generate_tickets(prediction, marks)
        if len(marks) != 5 or not isinstance(tickets, list):
            return {"status": "incomplete-prediction", "predictionStatus": "disabled"}
        working = copy.deepcopy(detail)
        working["predictionStatus"] = "ready"
        working["predictionModelVersion"] = prediction["modelVersion"]
        working["prediction"] = prediction
        working["predictionMarks"] = marks
        working["recommendedBets"] = tickets
        marks_by_number = {int(x["horseNumber"]): x["mark"] for x in marks}
        for horse in working["horses"]:
            if isinstance(horse, dict):
                no = int(horse.get("horseNumber") or 0)
                if no in marks_by_number:
                    horse["predMark"] = marks_by_number[no]
        lock = {
            "raceId": working["id"], "raceDate": working["date"],
            "capturedAtEpoch": int(now.timestamp()), "markCount": len(marks),
            "modelVersion": prediction["modelVersion"],
            "horses": [{"horseNumber": int(h["horseNumber"]),
                        "mark": marks_by_number.get(int(h["horseNumber"]), "")}
                       for h in active],
        }
        # Promote to a genuine frozen per-method receipt only after the
        # pre-off lock is committed into the same D1 detail. Its opinions were
        # computed on the original earlier card, never from finish/payout.
        method_receipt = working.get("fusionMethodPreoffReceipt")
        if isinstance(method_receipt, dict):
            try:
                captured = datetime.fromisoformat(
                    str(method_receipt["capturedAt"]).replace("Z","+00:00"))
                same = (method_receipt.get("raceId")==working["id"]
                        and method_receipt.get("raceDate")==working["date"]
                        and method_receipt.get("circuit")==working.get("circuit")
                        and captured.tzinfo and captured < post
                        and method_receipt.get("sourceKind")=="preoff-method-opinions-unsealed"
                        and set((method_receipt.get("arms") or {}).keys()) ==
                           set((prediction.get("methodEvidence") or {}).keys()))
                if same:
                    frozen = copy.deepcopy(method_receipt)
                    frozen["sourceKind"] = "original-frozen-preoff-method-opinions"
                    working["preRaceMethodOriginal"] = frozen
            except (KeyError, ValueError, TypeError):
                pass
        sealed = seal_detail(working, lock, now)
        return {"status": "sealed", "detail": sealed,
                "revision": sealed["preRacePrediction"]["sealRevision"]}
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
        # The current 60/40 model must have complete measured active runners.
        # A retrospective old model must never fill missing margin/corner rows.
        if ranked.get("predictionStatus") != "ready":
            return {"status": "incomplete-prediction",
                    "observedCoverage": ranked.get("observedModelCoverage") or {},
                    "predictionStatus": ranked.get("predictionStatus") or "unavailable"}
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
        # The new 60/40 forecast builder verifies both exact model identity
        # and complete measured-runner coverage. These are properties of the
        # freshly ranked active field, not of the old unranked D1 racecard.
        for key in ("honmeiDecision", "factorRanking", "markEngineVersion",
                    "predictionModelVersion", "predictionStatus",
                    "observedModelCoverage", "winConfidenceEvidence"):
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


def encode_sealed_d1_sync_detail(detail: dict, *, max_row_bytes: int = 1_800_000) -> dict:
    """Match Full Prefetch's lossless D1 row transport.

    The sealer reads a restored complete career, but MUST NOT upsert a large
    uncompressed record into the D1 race_details row. Repack the full original
    losslessly, preserve its history/locked forecast, and reject oversized rows.
    """
    from arvexq.ingest.full_snapshot_codec import KEY, pack_detail, unpack_detail
    if not isinstance(detail, dict) or not detail.get("id"):
        raise ValueError("race identity required for pre-race sync")
    packed = pack_detail(detail)
    # JSON object keys are strings. Stage64 probability maps may hold integer
    # horse-number keys in memory; compare the actual JSON transport contract.
    expected = json.loads(json.dumps(detail, ensure_ascii=False, allow_nan=False))
    if unpack_detail(packed) != expected or KEY not in packed:
        raise ValueError("lossless seal transport verification failed")
    row_size = len(json.dumps(packed, ensure_ascii=False, separators=(",", ":"),
                              allow_nan=False).encode("utf-8"))
    if row_size > max_row_bytes:
        raise ValueError(f"full sealed race row exceeds safe D1 budget: {row_size}")
    return packed


def capture_original_bet(detail: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Execute the actual client betting core before the off, never on results."""
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        raise ValueError("refusing post-off ticket generation")
    # Reuse the pre-off empirical fusion products already calculated in prepare_seal.
    # No separate selector, betting model, endpoint or post-off calculation.
    if (detail.get("predictionStatus") == "ready"
            and detail.get("predictionModelVersion") == "arvexq-empirical-fusion-v1"):
        items = detail.get("recommendedBets")
        if not isinstance(items, list) or any(
                not isinstance(item, dict) or not item.get("combos") for item in items):
            raise ValueError("empirically fused ticket record unavailable")
        return {
            "raceId": str(detail["id"]),
            "fixedAt": now.isoformat(timespec="seconds"),
            "fixedBeforePost": True,
            "fixedMinutesBeforePost": int((post - now).total_seconds() // 60),
            "decision": "推奨" if items else "見送り", "items": copy.deepcopy(items),
            "modelVersion": detail["predictionModelVersion"],
            "lockPolicy": "server-empirical-fusion-original-v1-no-post-hoc",
        }
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
    # Excluded Banei is intentionally listed in some archived D1 day manifests,
    # but the active pre-race sealer must never request or recreate its races.
    races = [r for r in (day_body.get("races") or [])
             if isinstance(r, dict) and r.get("id")
             and str(r.get("track") or "") not in ("帯広", "帯広ば")
             and not any(f"-{track}-" in str(r["id"]) for track in ("帯広", "帯広ば"))]
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
            old = fetch_existing_d1_detail(base, rid, now=datetime.now(JST))
            if not old:
                return {"id": rid, "status": "missing-detail"}
            if _active_history_missing(old) and old.get("analysisMode") not in ("新馬", "障害"):
                try:
                    old = recover_prior_history_before_post(old, now=datetime.now(JST))
                except Exception as exc:
                    return {"id": rid, "status": "missing-historical-evidence",
                            "reason": f"{type(exc).__name__}: {exc}"[:250]}
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
                "summaries": [], "details": [encode_sealed_d1_sync_detail(detail)],
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
