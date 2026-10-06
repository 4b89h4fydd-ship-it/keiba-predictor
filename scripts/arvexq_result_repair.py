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
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from arvexq.results import (
    JST,
    TERMINAL_NO_PAYOUT,
    merge_detail,
    merge_result,
    result_state,
    row_date,
    start_minutes,
    started,
)

# Transitional compatibility for history/validation callers while result-domain
# helpers now live in arvexq.results. New code should import the domain module.
_merge_detail = merge_detail
_merge_result = merge_result
_result_state = result_state
_row_date = row_date
_start_minutes = start_minutes
_started = started


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
    started_ids = [str(r["id"]) for r in rows if started(r, now)]
    pending = []
    for rid in started_ids:
        result_ok, payout_ok, _ = result_state(by_id.get(rid))
        if not result_ok or not payout_ok:
            pending.append(rid)

    pending.sort(key=lambda rid: (row_date(summary_by_id[rid]), start_minutes(summary_by_id[rid]), rid))
    errors: dict[str, str] = {}
    repaired: set[str] = set()

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

    for attempt in (1, 2):
        todo = []
        for rid in pending:
            result_ok, payout_ok, _ = result_state(by_id.get(rid))
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
                merged = merge_detail(by_id.get(rid), fresh)
                by_id[rid] = merged
                _seed_base(rid, merged)
                result_ok, payout_ok, _ = result_state(merged)
                if result_ok and payout_ok:
                    repaired.add(rid)
                    errors.pop(rid, None)
        if attempt == 1:
            unresolved_now = [rid for rid in todo if not all(result_state(by_id.get(rid))[:2])]
            if unresolved_now:
                time.sleep(float(os.getenv("ARVEXQ_RESULT_RETRY_SLEEP_SEC", "2")))

    summaries = []
    for row in rows:
        z = copy.deepcopy(row)
        rid = str(z.get("id") or "")
        detail = by_id.get(rid)
        result = (detail or {}).get("result") or z.get("result") or {}
        status = str(result.get("status") or "")
        result_ok, _, _ = result_state(detail)
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
        result_ok, payout_ok, status = result_state(detail)
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

    detail_payload = [
        by_id[rid] for rid in sorted(repaired)
        if isinstance(by_id.get(rid), dict) and by_id[rid].get("id")
    ]
    payload = {
        "summaries": summaries,
        "details": detail_payload,
        "meta": {
            "source": "github-actions-result-repair-v6-domain-split",
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
