#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build complete ARVEXQ race snapshots ahead of user taps.

This is the heavy lane. It runs separately from five-minute live sync, prepares
all available race cards/analysis, fingerprints prediction inputs, and skips
re-analysis when the prepared fingerprint is unchanged.
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
from arvexq.pipeline.fingerprints import active_horses, analysis_input_hash

JST = timezone(timedelta(hours=9))


def _read(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(path: str, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _card_usable(detail: dict[str, Any] | None) -> bool:
    if not isinstance(detail, dict) or not detail.get("id"):
        return False
    active = active_horses(detail)
    if len(active) < 2:
        return False
    if any(not str(h.get("name") or "").strip() for h in active):
        return False
    banei = "帯広" in str(detail.get("id") or "") or str(detail.get("track") or "").startswith("帯広")
    core = 0
    for horse in active:
        jockey = str(horse.get("jockey") or "").strip()
        try:
            weight = float(horse.get("carriedWeight") or horse.get("weight") or 0)
        except Exception:
            weight = 0.0
        if jockey and (banei or weight > 0):
            core += 1
    return len(active) < 4 or core >= max(3, (len(active) * 7 + 9) // 10)


def _analysis_ready(detail: dict[str, Any] | None) -> bool:
    pm = (detail or {}).get("preparedMeta") or {}
    return bool(pm.get("diagnosisReady"))


def _analysis_current(detail: dict[str, Any] | None) -> bool:
    if not isinstance(detail, dict) or not _analysis_ready(detail):
        return False
    pm = detail.get("preparedMeta") if isinstance(detail.get("preparedMeta"), dict) else {}
    saved = str(pm.get("analysisInputHash") or "")
    return bool(saved) and saved == analysis_input_hash(detail)


def _snapshot(rid: str) -> dict[str, Any] | None:
    detail = app._prepared_get_fresh(rid) or app._racedb_get_fast(rid) or app._fast_local_race_detail(rid)
    if not isinstance(detail, dict):
        return None
    try:
        compact = app._compact_display_snapshot(detail)
        return compact if isinstance(compact, dict) else detail
    except Exception:
        return detail


def _decorate(detail: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(detail)
    pm = dict(out.get("preparedMeta") or {})
    active = active_horses(out)
    with_history = sum(
        1 for h in active
        if h.get("recentRaces") or h.get("allPastRuns") or h.get("debutNoHistory")
    )
    pm["analysisInputHash"] = analysis_input_hash(out)
    pm["analysisInputHashVersion"] = "arvexq-analysis-input-v1"
    pm["prefetchedAtEpoch"] = int(time.time())
    pm["dataVersion"] = str(getattr(app, "ARVEXQ_DATA_CORE_VERSION", ""))
    pm["predictionVersion"] = str(getattr(app, "PREDICTION_ENGINE_VERSION", ""))
    pm["cardComplete"] = _card_usable(out)
    pm["historyCoverage"] = round(with_history / max(1, len(active)), 4) if active else 0.0
    out["preparedMeta"] = pm
    return out


def prepare(bundle_path: str, payload_path: str, report_path: str, workers: int) -> int:
    bundle = _read(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    initial = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id")]
    by_id: dict[str, dict[str, Any]] = {str(d["id"]): d for d in initial}
    errors: dict[str, str] = {}
    skipped_unchanged: list[str] = []

    def prepare_one(rid: str) -> tuple[str, dict[str, Any] | None, str, bool]:
        current = _snapshot(rid) or by_id.get(rid)
        if _card_usable(current) and _analysis_current(current):
            return rid, current, "", True
        try:
            detail = app._prepare_race_snapshot(rid, force=True)
        except Exception as exc:
            detail = None
            errors[rid] = f"{type(exc).__name__}: {exc}"
        latest = _snapshot(rid) or detail or current
        if isinstance(latest, dict) and latest.get("id"):
            return rid, latest, errors.get(rid, ""), False
        return rid, None, errors.get(rid, "no usable snapshot"), False

    ids = [str(r["id"]) for r in rows]
    targets = [
        rid for rid in ids
        if not (_card_usable(by_id.get(rid)) and _analysis_current(by_id.get(rid)))
    ]
    skipped_unchanged.extend(rid for rid in ids if rid not in targets)
    print(
        f"FULL_PREFETCH races={len(ids)} targets={len(targets)} "
        f"unchanged={len(skipped_unchanged)}"
    )

    if targets:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(targets)))) as pool:
            futures = {pool.submit(prepare_one, rid): rid for rid in targets}
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    rid, detail, error, unchanged = fut.result()
                except Exception as exc:
                    detail, error, unchanged = None, f"{type(exc).__name__}: {exc}", False
                if detail:
                    by_id[rid] = detail
                if unchanged and rid not in skipped_unchanged:
                    skipped_unchanged.append(rid)
                if error:
                    errors[rid] = error
                    print("FULL_PREFETCH_WARN", rid, error)

    decorated: dict[str, dict[str, Any]] = {}
    for rid in ids:
        detail = by_id.get(rid) or _snapshot(rid)
        if isinstance(detail, dict) and detail.get("id"):
            decorated[rid] = _decorate(detail)

    missing_card = [rid for rid in ids if not _card_usable(decorated.get(rid))]
    missing_analysis = [
        rid for rid in ids
        if _card_usable(decorated.get(rid)) and not _analysis_ready(decorated.get(rid))
    ]
    analysis_count = sum(1 for rid in ids if _analysis_ready(decorated.get(rid)))
    card_count = sum(1 for rid in ids if _card_usable(decorated.get(rid)))

    payload = {
        "summaries": rows,
        "details": [decorated[rid] for rid in ids if rid in decorated],
        "meta": {
            "source": "github-actions-full-prefetch-v2-hash",
            "sync_date": bundle.get("date") or "",
            "race_count": len(ids),
            "detail_count": len(decorated),
            "card_complete_count": card_count,
            "analysis_count": analysis_count,
            "analysis_skipped_unchanged_count": len(set(skipped_unchanged)),
            "missing_card_count": len(missing_card),
            "missing_analysis_count": len(missing_analysis),
            "display_complete": bool(ids) and not missing_card,
            "analysis_complete": bool(ids) and not missing_card and not missing_analysis,
            "prefetched_at": int(datetime.now(JST).timestamp()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "races": len(ids),
        "details": len(decorated),
        "cards_ready": card_count,
        "analysis_ready": analysis_count,
        "analysis_skipped_unchanged": sorted(set(skipped_unchanged)),
        "missing_card": missing_card,
        "missing_analysis": missing_analysis,
        "errors": errors,
    }
    _write(payload_path, payload)
    _write(report_path, report)
    print(
        "FULL_PREFETCH_AUDIT",
        f"races={len(ids)}",
        f"cards={card_count}",
        f"analysis={analysis_count}",
        f"unchanged={len(set(skipped_unchanged))}",
        f"missing_card={len(missing_card)}",
        f"missing_analysis={len(missing_analysis)}",
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="bundle.json")
    parser.add_argument("--payload", default="prefetch-payload.json")
    parser.add_argument("--report", default="prefetch-report.json")
    parser.add_argument("--workers", type=int, default=int(os.getenv("ARVEXQ_PREFETCH_WORKERS", "6")))
    args = parser.parse_args()
    return prepare(args.bundle, args.payload, args.report, args.workers)


if __name__ == "__main__":
    raise SystemExit(main())
