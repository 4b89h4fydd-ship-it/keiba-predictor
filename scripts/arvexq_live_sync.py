#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ lightweight live-sync lane.

This lane deliberately avoids full-card hydration and prediction rebuilds.
FULL PREFETCH owns stable race data/analysis. RESULT REPAIR owns old missed
results. LIVE SYNC only updates volatile fields for races that are live/nearby.
"""
from __future__ import annotations

import argparse
import json
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


def read_json(path: str, fallback: Any) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return fallback


def start_min(row: dict[str, Any]) -> int:
    st = str(row.get("startTime") or row.get("scheduledStartTime") or "")
    try:
        h, m = st.split(":", 1)
        return int(h) * 60 + int(m[:2])
    except Exception:
        return 9999


def terminal(detail: dict[str, Any] | None) -> bool:
    result = (detail or {}).get("result") or {}
    status = str(result.get("status") or "")
    if status in {"中止", "取止", "取消", "不成立"}:
        return True
    ranks = {
        int(x.get("finish") or 0)
        for x in (result.get("finishers") or [])
        if isinstance(x, dict)
    }
    return status == "確定" and all(x in ranks for x in (1, 2, 3))


def snapshot(rid: str) -> dict[str, Any] | None:
    d = (
        app._prepared_get_fresh(rid)
        or app._racedb_get_fast(rid)
        or app._fast_local_race_detail(rid)
    )
    if not isinstance(d, dict):
        return None
    try:
        compact = app._compact_display_snapshot(d)
        return compact if isinstance(compact, dict) else d
    except Exception:
        return d


def detail_safe_for_replace(detail: dict[str, Any] | None) -> bool:
    """Do not let a thin live snapshot replace a rich precomputed D1 payload."""
    if not isinstance(detail, dict) or not detail.get("id"):
        return False
    horses = [
        h for h in (detail.get("horses") or [])
        if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
    ]
    if not horses:
        return False
    active = [
        h for h in horses
        if not h.get("scratched")
        and str(h.get("status") or "") not in {"取消", "除外", "競走除外", "競走取消"}
    ] or horses
    if any(not str(h.get("name") or "").strip() for h in active):
        return False
    pm = detail.get("preparedMeta") if isinstance(detail.get("preparedMeta"), dict) else {}
    return bool(pm.get("diagnosisReady") or detail.get("preRacePrediction") or detail.get("predictionAudit"))


def horse_live_rows(detail: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rid = str(detail.get("id") or "")
    for h in detail.get("horses") or []:
        if not isinstance(h, dict):
            continue
        no = int(h.get("horseNumber") or 0)
        if not rid or no <= 0:
            continue
        out.append(
            {
                "race_id": rid,
                "horse_no": no,
                "win_odds": h.get("winOdds"),
                "popularity": h.get("popularity"),
                "body_weight": h.get("bodyWeight"),
                "body_weight_change": h.get("bodyWeightChange"),
                "horse_status": h.get("status") or ("取消" if h.get("scratched") else ""),
                "updated_at": int(time.time()),
            }
        )
    return out


def merge_summary(row: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    z = dict(row)
    if not detail:
        return z
    for key in ("weather", "condition", "surface", "distance", "title"):
        value = detail.get(key)
        if value not in (None, "", 0, "不明"):
            z[key] = value
    result = detail.get("result") or {}
    if str(result.get("status") or ""):
        z["raceStatus"] = result.get("status")
    return z


def choose_targets(rows: list[dict[str, Any]], now_min: int) -> list[str]:
    # One live/next race per venue first, then all races close to post time.
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((str(r.get("circuit") or ""), str(r.get("track") or "")), []).append(r)

    ids: list[str] = []
    for group in groups.values():
        group.sort(key=start_min)
        live = [r for r in group if start_min(r) <= now_min < start_min(r) + 35]
        future = [r for r in group if start_min(r) >= now_min]
        for r in live[:1] + future[:1]:
            rid = str(r.get("id") or "")
            if rid and rid not in ids:
                ids.append(rid)

    for r in sorted(rows, key=lambda x: abs(start_min(x) - now_min)):
        sm = start_min(r)
        rid = str(r.get("id") or "")
        if rid and -15 <= sm - now_min <= 60 and rid not in ids:
            ids.append(rid)
    return ids


def refresh_one(rid: str, now_min: int, row_by_id: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any] | None, str]:
    errors: list[str] = []
    row = row_by_id.get(rid) or {}
    sm = start_min(row)

    # Market/body weight/status lane. No diagnosis/history rebuild here.
    try:
        app.odds_refresh(rid, 1)
    except Exception as exc:
        errors.append("market:" + str(exc))

    # Recent result only. Old misses are handled by RESULT REPAIR.
    if sm < 9999 and now_min >= sm + 2:
        d0 = snapshot(rid)
        if not terminal(d0):
            try:
                app._refresh_result_fast(rid)
            except Exception as exc:
                errors.append("result:" + str(exc))

    return rid, snapshot(rid), "; ".join(errors)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="bundle.json")
    p.add_argument("--out", default="live-payload.json")
    p.add_argument("--audit", default="live-audit.json")
    p.add_argument("--workers", type=int, default=10)
    args = p.parse_args()

    bundle = read_json(args.bundle, {})
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    if not rows:
        raise SystemExit("live sync: no races in bundle")

    now = datetime.now(JST)
    now_min = now.hour * 60 + now.minute
    row_by_id = {str(r["id"]): r for r in rows}
    targets = choose_targets(rows, now_min)

    details: list[dict[str, Any]] = []
    odds_current: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    refreshed: dict[str, dict[str, Any]] = {}
    skipped_thin: list[str] = []

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as ex:
        futs = {ex.submit(refresh_one, rid, now_min, row_by_id): rid for rid in targets}
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                rid, d, err = fut.result()
            except Exception as exc:
                d, err = None, str(exc)
            if err:
                errors[rid] = err
            if isinstance(d, dict) and d.get("id"):
                refreshed[rid] = d
                odds_current.extend(horse_live_rows(d))
                if detail_safe_for_replace(d):
                    details.append(d)
                else:
                    skipped_thin.append(rid)

    summaries = [merge_summary(r, refreshed.get(str(r.get("id") or ""))) for r in rows]
    payload = {
        "summaries": summaries,
        "details": details,
        "odds_current": odds_current,
        "meta": {
            "source": "github-actions-live-delta-v2",
            "sync_date": bundle.get("date") or now.strftime("%Y-%m-%d"),
            "live_delta": True,
            "full_card_lane": False,
            "target_count": len(targets),
            "detail_update_count": len(details),
            "thin_detail_skipped_count": len(skipped_thin),
            "odds_row_count": len(odds_current),
            "error_count": len(errors),
            "live_updated_at": int(time.time()),
        },
    }
    audit = {
        "date": payload["meta"]["sync_date"],
        "targets": targets,
        "updated": sorted(refreshed),
        "thin_detail_skipped": sorted(skipped_thin),
        "errors": errors,
        "targetCount": len(targets),
        "updatedCount": len(refreshed),
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "LIVE SYNC",
        "targets=", len(targets),
        "details=", len(details),
        "thinSkipped=", len(skipped_thin),
        "oddsRows=", len(odds_current),
        "errors=", len(errors),
    )
    for rid, err in errors.items():
        print(" -", rid, err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
