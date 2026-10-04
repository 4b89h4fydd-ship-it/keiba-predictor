#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build complete ARVEXQ race snapshots ahead of user taps.

This is the heavy lane.  It runs separately from five-minute live sync, prepares
all available race cards/analysis once, adds deterministic metadata, and emits a
Cloudflare /api/sync payload containing rich full-detail snapshots.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
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


def _read(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(path: str, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _active_horses(detail: dict[str, Any]) -> list[dict[str, Any]]:
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0]
    active = [h for h in horses if not h.get("scratched") and str(h.get("status") or "") not in {"取消", "除外", "競走除外", "競走取消"}]
    return active or horses


def _card_usable(detail: dict[str, Any] | None) -> bool:
    if not isinstance(detail, dict) or not detail.get("id"):
        return False
    active = _active_horses(detail)
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


def _snapshot(rid: str) -> dict[str, Any] | None:
    detail = app._prepared_get_fresh(rid) or app._racedb_get_fast(rid) or app._fast_local_race_detail(rid)
    if not isinstance(detail, dict):
        return None
    try:
        compact = app._compact_display_snapshot(detail)
        return compact if isinstance(compact, dict) else detail
    except Exception:
        return detail


def _analysis_input_hash(detail: dict[str, Any]) -> str:
    """Fingerprint inputs without changing the prediction algorithm itself."""
    horse_rows = []
    for horse in sorted(_active_horses(detail), key=lambda h: int(h.get("horseNumber") or 999)):
        horse_rows.append({
            "horseNumber": horse.get("horseNumber"),
            "name": horse.get("name"),
            "sex": horse.get("sex"),
            "age": horse.get("age"),
            "carriedWeight": horse.get("carriedWeight") or horse.get("weight"),
            "jockey": horse.get("jockey"),
            "trainer": horse.get("trainer"),
            "bodyWeight": horse.get("bodyWeight"),
            "bodyWeightChange": horse.get("bodyWeightChange"),
            "recentRaces": horse.get("recentRaces") or horse.get("allPastRuns") or [],
            "pedigree": horse.get("pedigree") or horse.get("bloodline") or {},
        })
    value = {
        "id": detail.get("id"),
        "track": detail.get("track"),
        "surface": detail.get("surface"),
        "distance": detail.get("distance"),
        "weather": detail.get("weather"),
        "condition": detail.get("condition"),
        "horses": horse_rows,
    }
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()


def _decorate(detail: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(detail)
    pm = dict(out.get("preparedMeta") or {})
    active = _active_horses(out)
    with_history = sum(1 for h in active if h.get("recentRaces") or h.get("allPastRuns") or h.get("debutNoHistory"))
    pm["analysisInputHash"] = _analysis_input_hash(out)
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

    def prepare_one(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        current = _snapshot(rid) or by_id.get(rid)
        if _card_usable(current) and _analysis_ready(current):
            return rid, current, ""
        try:
            detail = app._prepare_race_snapshot(rid, force=True)
        except Exception as exc:
            detail = None
            errors[rid] = f"{type(exc).__name__}: {exc}"
        latest = _snapshot(rid) or detail or current
        if isinstance(latest, dict) and latest.get("id"):
            return rid, latest, errors.get(rid, "")
        return rid, None, errors.get(rid, "no usable snapshot")

    ids = [str(r["id"]) for r in rows]
    targets = [rid for rid in ids if not (_card_usable(by_id.get(rid)) and _analysis_ready(by_id.get(rid)))]
    print(f"FULL_PREFETCH races={len(ids)} targets={len(targets)}")

    if targets:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(targets)))) as pool:
            futures = {pool.submit(prepare_one, rid): rid for rid in targets}
            for fut in as_completed(futures):
                rid, detail, error = fut.result()
                if detail:
                    by_id[rid] = detail
                if error:
                    errors[rid] = error
                    print("FULL_PREFETCH_WARN", rid, error)

    decorated: dict[str, dict[str, Any]] = {}
    for rid in ids:
        detail = by_id.get(rid) or _snapshot(rid)
        if isinstance(detail, dict) and detail.get("id"):
            decorated[rid] = _decorate(detail)

    missing_card = [rid for rid in ids if not _card_usable(decorated.get(rid))]
    missing_analysis = [rid for rid in ids if _card_usable(decorated.get(rid)) and not _analysis_ready(decorated.get(rid))]
    analysis_count = sum(1 for rid in ids if _analysis_ready(decorated.get(rid)))
    card_count = sum(1 for rid in ids if _card_usable(decorated.get(rid)))

    payload = {
        "summaries": rows,
        "details": [decorated[rid] for rid in ids if rid in decorated],
        "meta": {
            "source": "github-actions-full-prefetch-v1",
            "sync_date": bundle.get("date") or "",
            "race_count": len(ids),
            "detail_count": len(decorated),
            "card_complete_count": card_count,
            "analysis_count": analysis_count,
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
