#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARVEXQ lightweight live-sync lane.

FULL PREFETCH owns stable card/analysis data. RESULT REPAIR owns long-tail
result misses. LIVE SYNC reads the rich D1 detail as its merge base and changes
only volatile fields, so a stale/thin local cache can never erase a prepared
race card.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app

JST = timezone(timedelta(hours=9))
D1_BASE = os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")
TERMINAL = {"中止", "取止", "取消", "不成立"}
LIVE_HORSE_FIELDS = (
    "winOdds", "popularity", "bodyWeight", "bodyWeightChange",
    "status", "scratched", "oddsSource", "oddsForecast",
)


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
    if status in TERMINAL:
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


def fetch_d1_detail(rid: str) -> dict[str, Any] | None:
    """Get the authoritative prepared payload used as the non-destructive base."""
    url = f"{D1_BASE}/api/race/{urllib.parse.quote(rid, safe='')}?t={int(time.time())}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ARVEXQ-LiveSync/1"})
        with urllib.request.urlopen(req, timeout=8) as res:
            body = json.loads(res.read().decode("utf-8"))
        detail = body.get("detail") if isinstance(body, dict) else None
        return detail if isinstance(detail, dict) and detail.get("id") else None
    except Exception as exc:
        print("D1_BASE_FETCH_ERROR", rid, type(exc).__name__, exc)
        return None


def _merge_horses(base: list[Any], fresh: list[Any]) -> list[dict[str, Any]]:
    base_rows = [copy.deepcopy(h) for h in base if isinstance(h, dict)]
    by_no = {
        int(h.get("horseNumber") or 0): h
        for h in base_rows
        if int(h.get("horseNumber") or 0) > 0
    }
    for raw in fresh:
        if not isinstance(raw, dict):
            continue
        no = int(raw.get("horseNumber") or 0)
        if no <= 0:
            continue
        row = by_no.get(no)
        if row is None:
            # Only use a new runner when there is no prepared runner with that number.
            row = {"horseNumber": no}
            for key in ("frameNumber", "name"):
                if raw.get(key) not in (None, ""):
                    row[key] = copy.deepcopy(raw[key])
            base_rows.append(row)
            by_no[no] = row
        for key in LIVE_HORSE_FIELDS:
            if key in raw and raw.get(key) not in (None, ""):
                row[key] = copy.deepcopy(raw[key])
    return base_rows


def _merge_result(old: Any, new: Any) -> dict[str, Any]:
    old_r = copy.deepcopy(old) if isinstance(old, dict) else {}
    new_r = new if isinstance(new, dict) else {}
    if not new_r:
        return old_r
    old_final = str(old_r.get("status") or "") == "確定" and bool(old_r.get("finishers"))
    new_final = str(new_r.get("status") or "") == "確定" and bool(new_r.get("finishers"))
    # Never downgrade a final result to a sparse/flash response.
    if old_final and not new_final:
        return old_r
    out = old_r
    for key, value in new_r.items():
        if value not in (None, "", [], {}):
            out[key] = copy.deepcopy(value)
    return out


def merge_live(base: dict[str, Any] | None, fresh: dict[str, Any] | None, market: dict[str, Any] | None) -> dict[str, Any] | None:
    """Overlay volatile source data on a rich prepared payload without degrading it."""
    if not isinstance(base, dict):
        base = {}
    if not isinstance(fresh, dict):
        fresh = {}
    if not isinstance(market, dict):
        market = {}
    if not base and not fresh:
        return None

    out = copy.deepcopy(base or fresh)
    for key in (
        "weather", "condition", "surface", "distance", "title",
        "startTime", "scheduledStartTime", "fieldSize",
        "oddsSource", "oddsType", "oddsUpdatedAt",
    ):
        value = fresh.get(key)
        if value not in (None, "", 0, "不明"):
            out[key] = copy.deepcopy(value)

    fresh_horses = [h for h in (fresh.get("horses") or []) if isinstance(h, dict)]
    market_horses = [h for h in (market.get("horses") or []) if isinstance(h, dict)]
    if out.get("horses") or fresh_horses or market_horses:
        horses = _merge_horses(out.get("horses") or [], fresh_horses)
        horses = _merge_horses(horses, market_horses)
        out["horses"] = horses

    if fresh.get("result"):
        out["result"] = _merge_result(out.get("result"), fresh.get("result"))

    # Stable/pre-race fields always come from the prepared base when one exists.
    if base:
        for key in (
            "preparedMeta", "preRacePrediction", "predictionAudit", "aiEvaluation",
            "analysisMode", "pace", "pacePrediction", "volatility",
        ):
            if key in base:
                out[key] = copy.deepcopy(base[key])

    pm = dict(out.get("preparedMeta") or {})
    pm["liveUpdatedAtEpoch"] = int(time.time())
    out["preparedMeta"] = pm
    return out


def detail_safe_for_replace(detail: dict[str, Any] | None) -> bool:
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
        out.append({
            "race_id": rid,
            "horse_no": no,
            "win_odds": h.get("winOdds"),
            "popularity": h.get("popularity"),
            "body_weight": h.get("bodyWeight"),
            "body_weight_change": h.get("bodyWeightChange"),
            "horse_status": h.get("status") or ("取消" if h.get("scratched") else ""),
            "updated_at": int(time.time()),
        })
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


def refresh_one(rid: str, now_min: int, row_by_id: dict[str, dict[str, Any]], bundled_detail: dict[str, Any] | None) -> tuple[str, dict[str, Any] | None, str, bool]:
    errors: list[str] = []
    row = row_by_id.get(rid) or {}
    sm = start_min(row)
    base = bundled_detail or fetch_d1_detail(rid)

    market: dict[str, Any] | None = None
    try:
        body = app.odds_refresh(rid, 1)
        market = body if isinstance(body, dict) else None
    except Exception as exc:
        errors.append("market:" + str(exc))

    fresh = snapshot(rid)
    reference = merge_live(base, fresh, market) or base or fresh
    if sm < 9999 and now_min >= sm + 2 and not terminal(reference):
        try:
            result_detail = app._refresh_result_fast(rid)
            if isinstance(result_detail, dict):
                fresh = result_detail
        except Exception as exc:
            errors.append("result:" + str(exc))

    merged = merge_live(base, fresh or snapshot(rid), market)
    return rid, merged, "; ".join(errors), bool(base)


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
    bundled_by_id = {
        str(d.get("id") or ""): d
        for d in (bundle.get("details") or [])
        if isinstance(d, dict) and d.get("id")
    }

    now = datetime.now(JST)
    now_min = now.hour * 60 + now.minute
    row_by_id = {str(r["id"]): r for r in rows}
    targets = choose_targets(rows, now_min)

    details: list[dict[str, Any]] = []
    odds_current: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    refreshed: dict[str, dict[str, Any]] = {}
    skipped_thin: list[str] = []
    missing_base: list[str] = []

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as ex:
        futs = {
            ex.submit(refresh_one, rid, now_min, row_by_id, bundled_by_id.get(rid)): rid
            for rid in targets
        }
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                rid, d, err, had_base = fut.result()
            except Exception as exc:
                d, err, had_base = None, str(exc), False
            if err:
                errors[rid] = err
            if not had_base:
                missing_base.append(rid)
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
            "source": "github-actions-live-delta-v3-d1-base",
            "sync_date": bundle.get("date") or now.strftime("%Y-%m-%d"),
            "live_delta": True,
            "full_card_lane": False,
            "target_count": len(targets),
            "detail_update_count": len(details),
            "thin_detail_skipped_count": len(skipped_thin),
            "missing_d1_base_count": len(missing_base),
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
        "missing_d1_base": sorted(missing_base),
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
        "missingD1Base=", len(missing_base),
        "oddsRows=", len(odds_current),
        "errors=", len(errors),
    )
    for rid, err in errors.items():
        print("LIVE_SYNC_ERROR", rid, err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
