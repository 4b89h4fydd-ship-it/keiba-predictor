#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ result repair lane.

Repairs every started race whose result or payout is incomplete.  It is designed
for GitHub Actions and deliberately does not rebuild diagnosis/history.  Rich
race-detail payloads are preserved while only authoritative live/result fields
are upgraded.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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


def _result_state(detail: dict[str, Any] | None) -> tuple[bool, bool, str]:
    d = detail if isinstance(detail, dict) else {}
    result = d.get("result") if isinstance(d.get("result"), dict) else {}
    status = str(result.get("status") or "")
    finishers = [x for x in (result.get("finishers") or []) if isinstance(x, dict)]
    ranks = {int(x.get("finish") or 0) for x in finishers}
    podium = all(x in ranks for x in (1, 2, 3))
    final = status == "確定" and podium
    if status in TERMINAL_NO_PAYOUT:
        return True, True, status
    payouts = result.get("payouts") if isinstance(result.get("payouts"), list) else []
    return final, bool(payouts), status


def _started(summary: dict[str, Any], now_minutes: int) -> bool:
    sm = _start_minutes(summary)
    return sm < 9999 and now_minutes >= sm + 2


def _merge_detail(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
    """Merge a refreshed result without degrading a precomputed rich card."""
    if not old:
        return copy.deepcopy(new or {})
    if not new:
        return copy.deepcopy(old)

    out = copy.deepcopy(old)
    for key, value in new.items():
        if key in {"horses", "preparedMeta", "preRacePrediction", "predictionAudit"}:
            continue
        if value not in (None, "", [], {}):
            out[key] = copy.deepcopy(value)

    # Live result/environment fields are authoritative when present.
    if isinstance(new.get("result"), dict) and new.get("result"):
        result = copy.deepcopy(old.get("result") or {})
        for key, value in new["result"].items():
            if value not in (None, "", [], {}):
                result[key] = copy.deepcopy(value)
        out["result"] = result

    # Never erase the prepared horse card/analysis while repairing a result.
    if old.get("horses"):
        out["horses"] = copy.deepcopy(old["horses"])
    if old.get("preparedMeta"):
        out["preparedMeta"] = copy.deepcopy(old["preparedMeta"])
    if old.get("preRacePrediction"):
        out["preRacePrediction"] = copy.deepcopy(old["preRacePrediction"])
    if old.get("predictionAudit"):
        out["predictionAudit"] = copy.deepcopy(old["predictionAudit"])
    return out


def repair(bundle_path: str, payload_path: str, report_path: str, workers: int = 6) -> int:
    bundle = _read_json(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    base_details = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id")]
    by_id: dict[str, dict[str, Any]] = {str(d["id"]): d for d in base_details}
    summary_by_id = {str(r["id"]): r for r in rows}

    now = datetime.now(JST)
    now_minutes = now.hour * 60 + now.minute

    started_ids = [str(r["id"]) for r in rows if _started(r, now_minutes)]
    pending = []
    for rid in started_ids:
        result_ok, payout_ok, status = _result_state(by_id.get(rid))
        if not result_ok or not payout_ok:
            pending.append(rid)

    # Oldest missing result first. No arbitrary 24-race cap.
    pending.sort(key=lambda rid: (_start_minutes(summary_by_id[rid]), rid))
    errors: dict[str, str] = {}
    repaired: set[str] = set()

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
                rid, fresh, error = fut.result()
                if error:
                    errors[rid] = error
                    print("RESULT_REPAIR_ERROR", rid, error)
                    continue
                merged = _merge_detail(by_id.get(rid), fresh)
                by_id[rid] = merged
                result_ok, payout_ok, _ = _result_state(merged)
                if result_ok and payout_ok:
                    repaired.add(rid)
                    errors.pop(rid, None)
        if attempt == 1:
            unresolved = [rid for rid in todo if not all(_result_state(by_id.get(rid))[:2])]
            if unresolved:
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
        if not result_ok:
            unresolved.append({
                "race_id": rid,
                "circuit": row.get("circuit") or "",
                "track": row.get("track") or "",
                "race_no": row.get("raceNumber") or row.get("raceNo") or "",
                "start_time": row.get("startTime") or "",
                "status": status,
                "error": errors.get(rid, "result still incomplete"),
            })
        elif not payout_ok:
            payout_missing.append({
                "race_id": rid,
                "circuit": row.get("circuit") or "",
                "track": row.get("track") or "",
                "race_no": row.get("raceNumber") or row.get("raceNo") or "",
                "start_time": row.get("startTime") or "",
                "status": status,
                "error": errors.get(rid, "payout still incomplete"),
            })

    # Send full rich detail snapshots so Cloudflare's replace-upsert cannot erase cards.
    detail_payload = [by_id[rid] for rid in started_ids if isinstance(by_id.get(rid), dict) and by_id[rid].get("id")]
    payload = {
        "summaries": summaries,
        "details": detail_payload,
        "meta": {
            "source": "github-actions-result-repair-v1",
            "sync_date": bundle.get("date") or "",
            "started_race_count": len(started_ids),
            "result_pending_before": len(pending),
            "result_repaired_count": len(repaired),
            "result_missing_count": len(unresolved),
            "payout_missing_count": len(payout_missing),
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
    }
    _write_json(payload_path, payload)
    _write_json(report_path, report)

    print(
        "RESULT_REPAIR_AUDIT",
        f"started={len(started_ids)}",
        f"pending_before={len(pending)}",
        f"repaired={len(repaired)}",
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
