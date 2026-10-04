#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repair only missing fields in one historical ARVEXQ day.

A rich D1 snapshot is the base. Complete cards are never rebuilt merely to get a
missing result/payout; only incomplete cards use the heavier race preparation.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
from arvexq.pipeline.fingerprints import active_horses
from scripts.arvexq_result_repair import _merge_detail, _result_state, _seed_base


def read_json(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def card_score(detail: dict[str, Any] | None) -> int:
    if not isinstance(detail, dict) or not detail.get("id"):
        return 0
    horses = active_horses(detail)
    if not horses:
        return 0
    named = sum(1 for h in horses if str(h.get("name") or "").strip())
    jockey = sum(1 for h in horses if str(h.get("jockey") or "").strip())
    banei = "帯広" in str(detail.get("id") or "") or str(detail.get("track") or "").startswith("帯広")
    weighted = 0
    history = 0
    for h in horses:
        try:
            if float(h.get("carriedWeight") or h.get("weight") or 0) > 0:
                weighted += 1
        except Exception:
            pass
        if h.get("recentRaces") or h.get("allPastRuns") or h.get("debutNoHistory"):
            history += 1
    core = named == len(horses) and (
        len(horses) < 4
        or (
            jockey >= max(3, (len(horses) * 7 + 9) // 10)
            and (banei or weighted >= max(3, (len(horses) * 7 + 9) // 10))
        )
    )
    return (100000 if core else 0) + named * 1000 + jockey * 100 + weighted * 50 + history * 10 + len(horses)


def card_complete(detail: dict[str, Any] | None) -> bool:
    if not isinstance(detail, dict):
        return False
    horses = active_horses(detail)
    if len(horses) < 2:
        return False
    expected = int(detail.get("fieldSize") or 0)
    if expected >= 4 and len(horses) < max(3, (expected * 7 + 9) // 10):
        return False
    return card_score(detail) >= 100000


def history_complete(detail: dict[str, Any] | None) -> bool:
    result_ok, payout_ok, _ = _result_state(detail)
    return card_complete(detail) and result_ok and payout_ok


def merge_history(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, Any]:
    if not old:
        return copy.deepcopy(new or {})
    if not new:
        return copy.deepcopy(old)
    out = _merge_detail(old, new)
    if card_score(new) > card_score(old):
        out["horses"] = copy.deepcopy(new.get("horses") or [])
        for key in ("fieldSize", "title", "surface", "distance", "weather", "condition"):
            value = new.get(key)
            if value not in (None, "", 0, "不明"):
                out[key] = copy.deepcopy(value)
    return out


def repair(bundle_path: str, payload_path: str, report_path: str, workers: int) -> int:
    bundle = read_json(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    details = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id")]
    by_id = {str(d["id"]): d for d in details}
    row_by_id = {str(r["id"]): r for r in rows}
    ids = [str(r["id"]) for r in rows]
    errors: dict[str, str] = {}
    result_only_repairs = 0
    card_repairs = 0

    def pending_ids() -> list[str]:
        return [rid for rid in ids if not history_complete(by_id.get(rid))]

    def repair_one(rid: str) -> tuple[str, dict[str, Any] | None, str, str]:
        base = by_id.get(rid)
        _seed_base(rid, base)
        try:
            if card_complete(base):
                fresh = app._refresh_result_fast(rid)
                return rid, fresh if isinstance(fresh, dict) else None, "", "result"
            fresh = app._prepare_race_snapshot(rid, force=True, manual=False)
            return rid, fresh if isinstance(fresh, dict) else None, "", "card"
        except Exception as exc:
            return rid, None, f"{type(exc).__name__}: {exc}", "card" if not card_complete(base) else "result"

    for attempt in (1, 2):
        pending = pending_ids()
        if not pending:
            break
        print(f"HISTORY_REPAIR pass={attempt} pending={len(pending)}")
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(pending)))) as pool:
            futures = {pool.submit(repair_one, rid): rid for rid in pending}
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    _, fresh, error, mode = fut.result()
                except Exception as exc:
                    fresh, error, mode = None, f"{type(exc).__name__}: {exc}", "unknown"
                if error:
                    errors[rid] = error
                    print("HISTORY_REPAIR_ERROR", rid, error)
                    continue
                if fresh:
                    by_id[rid] = merge_history(by_id.get(rid), fresh)
                    _seed_base(rid, by_id[rid])
                    if mode == "result":
                        result_only_repairs += 1
                    elif mode == "card":
                        card_repairs += 1
                    if history_complete(by_id.get(rid)):
                        errors.pop(rid, None)
        if attempt == 1 and pending_ids():
            time.sleep(float(os.getenv("ARVEXQ_HISTORY_RETRY_SLEEP_SEC", "2")))

    missing_card = []
    missing_result = []
    missing_payout = []
    for rid in ids:
        d = by_id.get(rid)
        if not card_complete(d):
            missing_card.append(rid)
        result_ok, payout_ok, _ = _result_state(d)
        if not result_ok:
            missing_result.append(rid)
        elif not payout_ok:
            missing_payout.append(rid)

    summaries = []
    for row in rows:
        z = copy.deepcopy(row)
        result = (by_id.get(str(z.get("id") or "")) or {}).get("result") or {}
        result_ok, _, status = _result_state(by_id.get(str(z.get("id") or "")))
        if status in {"中止", "取止", "取消", "不成立"}:
            z["raceStatus"] = status
        elif result_ok:
            z["raceStatus"] = "確定"
        elif result.get("finishers"):
            z["raceStatus"] = "速報"
        summaries.append(z)

    payload_details = [by_id[rid] for rid in ids if isinstance(by_id.get(rid), dict) and by_id[rid].get("id")]
    payload = {
        "summaries": summaries,
        "details": payload_details,
        "meta": {
            "source": "github-actions-history-missing-only-v2",
            "sync_date": bundle.get("date") or (rows[0].get("date") if rows else "") or "",
            "history_window_days": 7,
            "race_count": len(ids),
            "detail_count": len(payload_details),
            "result_only_repair_count": result_only_repairs,
            "card_repair_count": card_repairs,
            "missing_card_count": len(missing_card),
            "missing_result_count": len(missing_result),
            "missing_payout_count": len(missing_payout),
            "history_complete": bool(ids) and not missing_card and not missing_result and not missing_payout,
            "history_repaired_at": int(time.time()),
        },
    }
    report = {
        "date": payload["meta"]["sync_date"],
        "races": len(ids),
        "result_only_repairs": result_only_repairs,
        "card_repairs": card_repairs,
        "missing_card": missing_card,
        "missing_result": missing_result,
        "missing_payout": missing_payout,
        "errors": errors,
        "labels": {
            rid: f"{row_by_id[rid].get('circuit','')} {row_by_id[rid].get('track','')} {row_by_id[rid].get('raceNumber','')}R"
            for rid in ids
        },
    }
    Path(payload_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "HISTORY_REPAIR_AUDIT",
        "races=", len(ids),
        "resultOnly=", result_only_repairs,
        "cardRepairs=", card_repairs,
        "missingCard=", len(missing_card),
        "missingResult=", len(missing_result),
        "missingPayout=", len(missing_payout),
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="history-bundle.json")
    p.add_argument("--payload", default="history-payload.json")
    p.add_argument("--report", default="history-report.json")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    return repair(args.bundle, args.payload, args.report, args.workers)


if __name__ == "__main__":
    raise SystemExit(main())
