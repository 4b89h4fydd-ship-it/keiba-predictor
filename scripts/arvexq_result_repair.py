#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ result repair lane.

Repairs every started race whose result or payout is incomplete. Rich D1 race
payloads are seeded locally and preserved; only authoritative result/live fields
are upgraded. Pending races are oldest-first with no arbitrary race-count cap.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app

JST = timezone(timedelta(hours=9))
TERMINAL_NO_PAYOUT = {"中止", "取止", "取消", "不成立"}


def _read_json(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: str, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _start_minutes(row: dict[str, Any]) -> int:
    raw = str(row.get("startTime") or row.get("scheduledStartTime") or "")
    try:
        hh, mm = raw.split(":", 1)
        return int(hh) * 60 + int(mm[:2])
    except Exception:
        return 9999


def _row_date(row: dict[str, Any]) -> str:
    return str(row.get("date") or row.get("race_date") or row.get("raceDate") or "")


def _podium_final(result: Any) -> bool:
    """Accept normal and dead-heat podiums once the source marks them final.

    A dead heat can legally produce ranks such as 1,1,3 or 1,2,2. Requiring the
    literal rank set {1,2,3} leaves those races stuck in "result pending" forever.
    """
    if not isinstance(result, dict) or str(result.get("status") or "") != "確定":
        return False
    finishes: list[int] = []
    for row in result.get("finishers") or []:
        if not isinstance(row, dict):
            continue
        try:
            finish = int(row.get("finish") or 0)
        except Exception:
            finish = 0
        if finish > 0:
            finishes.append(finish)
    # Three classified horses occupying places 1-3 is enough even when a tie
    # means one nominal rank is skipped. Payout validation is handled separately.
    return 1 in finishes and sum(1 for finish in finishes if finish <= 3) >= 3


def _result_state(detail: dict[str, Any] | None) -> tuple[bool, bool, str]:
    d = detail if isinstance(detail, dict) else {}
    result = d.get("result") if isinstance(d.get("result"), dict) else {}
    status = str(result.get("status") or "")
    if status in TERMINAL_NO_PAYOUT:
        return True, True, status
    payouts = result.get("payouts") if isinstance(result.get("payouts"), list) else []
    return _podium_final(result), bool(payouts), status


def _started(summary: dict[str, Any], now: datetime) -> bool:
    """Historical dates are always started; today's races use post time + 2 min."""
    race_date = _row_date(summary)
    today = now.strftime("%Y-%m-%d")
    if race_date:
        if race_date < today:
            return True
        if race_date > today:
            return False
    sm = _start_minutes(summary)
    now_minutes = now.hour * 60 + now.minute
    return sm < 9999 and now_minutes >= sm + 2


def _merge_result(old: Any, new: Any) -> dict[str, Any]:
    old_r = copy.deepcopy(old) if isinstance(old, dict) else {}
    new_r = new if isinstance(new, dict) else {}
    if not new_r:
        return old_r
    old_final = _podium_final(old_r)
    new_final = _podium_final(new_r)
    out = old_r
    for key, value in new_r.items():
        if value in (None, "", [], {}):
            continue
        # A transient flash response must never downgrade a stored final result.
        if old_final and not new_final and key in {"status", "finishers"}:
            continue
        out[key] = copy.deepcopy(value)
    return out


def _merge_detail(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
    """Merge refreshed result data without degrading a precomputed rich card."""
    if not old:
        return copy.deepcopy(new or {})
    if not new:
        return copy.deepcopy(old)

    out = copy.deepcopy(old)
    protected = {
        "horses", "preparedMeta", "preRacePrediction", "predictionAudit",
        "aiEvaluation", "pace", "pacePrediction", "volatility",
    }
    for key, value in new.items():
        if key in protected or key == "result":
            continue
        if value not in (None, "", [], {}):
            out[key] = copy.deepcopy(value)

    if isinstance(new.get("result"), dict) and new.get("result"):
        out["result"] = _merge_result(old.get("result"), new.get("result"))

    for key in protected:
        if key in old:
            out[key] = copy.deepcopy(old[key])
    return out


def _seed_base(rid: str, detail: dict[str, Any] | None) -> None:
    if not isinstance(detail, dict) or not detail.get("id"):
        return
    try:
        app._store_fast_snapshot(copy.deepcopy(detail))
    except Exception as exc:
        print("RESULT_BASE_SEED_ERROR", rid, type(exc).__name__, exc)


def repair(bundle_path: str, payload_path: str, report_path: str, workers: int = 6) -> int:
    bundle = _read_json(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    base_details = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id")]
    by_id: dict[str, dict[str, Any]] = {str(d["id"]): d for d in base_details}
    summary_by_id = {str(r["id"]): r for r in rows}

    now = datetime.now(JST)
    started_ids = [str(r["id"]) for r in rows if _started(r, now)]
    pending = []
    for rid in started_ids:
        result_ok, payout_ok, _ = _result_state(by_id.get(rid))
        if not result_ok or not payout_ok:
            pending.append(rid)

    # Oldest missing result first. No arbitrary 24-race cap.
    pending.sort(key=lambda rid: (_row_date(summary_by_id[rid]), _start_minutes(summary_by_id[rid]), rid))
    errors: dict[str, str] = {}
    repaired: set[str] = set()

    # D1 is the current display source of truth. Seed its rich details so result
    # collectors do not start from an old/empty Actions cache.
    for rid in pending:
        _seed_base(rid, by_id.get(rid))

    def refresh_one(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        try:
            fresh = app._refresh_result_fast(rid)
            if not isinstance(fresh, dict) or not fresh.get("id"):
                return rid, None, "result refresher returned no usable detail"
            return rid, fresh, ""
        except Exception as exc:
            return rid, None, f"{type(exc).__name__}: {exc}"

    # Two bounded passes handle transient source failures while keeping runtime predictable.
    for attempt in (1, 2):
        todo = []
        for rid in pending:
            result_ok, payout_ok, _ = _result_state(by_id.get(rid))
            if not result_ok or not payout_ok:
                todo.append(rid)
        if not todo:
            break

        print(f"RESULT_REPAIR pass={attempt} pending={len(todo)}")
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(todo)))) as pool:
            futures = {pool.submit(refresh_one, rid): rid for rid in todo}
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    _, fresh, error = fut.result()
                except Exception as exc:
                    fresh, error = None, f"{type(exc).__name__}: {exc}"
                if error:
                    errors[rid] = error
                    print("RESULT_REPAIR_ERROR", rid, error)
                    continue
                merged = _merge_detail(by_id.get(rid), fresh)
                by_id[rid] = merged
                # Keep the improved merged result available to the second pass.
                _seed_base(rid, merged)
                result_ok, payout_ok, _ = _result_state(merged)
                if result_ok and payout_ok:
                    repaired.add(rid)
                    errors.pop(rid, None)
        if attempt == 1:
            unresolved_now = [rid for rid in todo if not all(_result_state(by_id.get(rid))[:2])]
            if unresolved_now:
                time.sleep(float(os.getenv("ARVEXQ_RESULT_RETRY_SLEEP_SEC", "2")))

    summaries = []
    for row in rows:
        z = copy.deepcopy(row)
        rid = str(z.get("id") or "")
        detail = by_id.get(rid)
        result = (detail or {}).get("result") or z.get("result") or {}
        status = str(result.get("status") or "")
        result_ok, _, _ = _result_state(detail)
        if status in TERMINAL_NO_PAYOUT:
            z["raceStatus"] = status
        elif result_ok:
            z["raceStatus"] = "確定"
        elif result.get("finishers"):
            z["raceStatus"] = "速報"
        summaries.append(z)

    unresolved = []
    payout_missing = []
    for rid in started_ids:
        detail = by_id.get(rid)
        result_ok, payout_ok, status = _result_state(detail)
        row = summary_by_id[rid]
        item = {
            "race_id": rid,
            "circuit": row.get("circuit") or "",
            "track": row.get("track") or "",
            "race_no": row.get("raceNumber") or row.get("raceNo") or "",
            "start_time": row.get("startTime") or "",
            "status": status,
            "error": errors.get(rid, ""),
        }
        if not result_ok:
            item["error"] = item["error"] or "result still incomplete"
            unresolved.append(item)
        elif not payout_ok:
            item["error"] = item["error"] or "payout still incomplete"
            payout_missing.append(item)

    # Write back only races whose result actually improved to a complete result.
    # Unresolved races already exist in D1; re-uploading their 1-3 MB rich cards
    # wastes time and was causing Worker 500/503 responses on every repair cycle.
    detail_payload = [
        by_id[rid] for rid in sorted(repaired)
        if isinstance(by_id.get(rid), dict) and by_id[rid].get("id")
    ]
    payload = {
        "summaries": summaries,
        "details": detail_payload,
        "meta": {
            "source": "github-actions-result-repair-v5-repaired-only",
            "sync_date": bundle.get("date") or "",
            "started_race_count": len(started_ids),
            "result_pending_before": len(pending),
            "result_repaired_count": len(repaired),
            "result_missing_count": len(unresolved),
            "payout_missing_count": len(payout_missing),
            "result_detail_write_count": len(detail_payload),
            "result_repair_complete": not unresolved and not payout_missing,
            "result_repair_at": int(now.timestamp()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "started": len(started_ids),
        "pending_before": len(pending),
        "repaired": sorted(repaired),
        "result_missing": unresolved,
        "payout_missing": payout_missing,
        "detail_write_count": len(detail_payload),
    }
    _write_json(payload_path, payload)
    _write_json(report_path, report)

    print(
        "RESULT_REPAIR_AUDIT",
        f"started={len(started_ids)}",
        f"pending_before={len(pending)}",
        f"repaired={len(repaired)}",
        f"detail_write_count={len(detail_payload)}",
        f"result_missing={len(unresolved)}",
        f"payout_missing={len(payout_missing)}",
    )
    for item in unresolved:
        print("RESULT_MISSING", json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    for item in payout_missing:
        print("PAYOUT_MISSING", json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="bundle.json")
    parser.add_argument("--payload", default="result-repair-payload.json")
    parser.add_argument("--report", default="result-repair-report.json")
    parser.add_argument("--workers", type=int, default=int(os.getenv("ARVEXQ_RESULT_WORKERS", "6")))
    args = parser.parse_args()
    return repair(args.bundle, args.payload, args.report, args.workers)


if __name__ == "__main__":
    raise SystemExit(main())
