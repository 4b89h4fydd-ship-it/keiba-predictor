#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build complete ARVEXQ race snapshots ahead of user taps.

This is the heavy lane. It runs separately from five-minute live sync, prepares
all available race cards, explicitly materializes the existing ARVEXQ diagnosis,
fingerprints prediction inputs, and skips re-analysis when that fingerprint is
unchanged. Prediction formulas/marks/bet rules remain owned by app.py.
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
from arvexq.prediction.race_intelligence import attach_evidence
from arvexq.ingest.fallback_enrichment import enrich_race_missing_sync
from arvexq.databanks.authorized_feeds import register_authorized_history_feeds
from arvexq.databanks.nar_official_csv import register_nar_official_archive
from arvexq.databanks.registry import registry as source_registry

JST = timezone(timedelta(hours=9))


def _read(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(path: str, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _meaningful(value: Any) -> bool:
    return value not in (None, "", [], {})


def _merge_horses(base: Any, fresh: Any) -> list[dict[str, Any]]:
    """Preserve the rich card while allowing newer diagnosis/live fields to win."""
    out = [copy.deepcopy(h) for h in (base or []) if isinstance(h, dict)]
    by_no: dict[int, dict[str, Any]] = {}
    for row in out:
        try:
            no = int(row.get("horseNumber") or 0)
        except Exception:
            no = 0
        if no > 0:
            by_no[no] = row

    for raw in fresh or []:
        if not isinstance(raw, dict):
            continue
        try:
            no = int(raw.get("horseNumber") or 0)
        except Exception:
            no = 0
        if no <= 0:
            continue
        row = by_no.get(no)
        if row is None:
            row = {"horseNumber": no}
            out.append(row)
            by_no[no] = row
        for key, value in raw.items():
            if key == "horseNumber":
                continue
            if _meaningful(value) or key not in row:
                row[key] = copy.deepcopy(value)
    return out


def _merge_detail(base: Any, fresh: Any) -> dict[str, Any]:
    """Merge snapshots without letting a thin/stale cache erase rich fields."""
    out = copy.deepcopy(base) if isinstance(base, dict) else {}
    new = fresh if isinstance(fresh, dict) else {}
    if not out:
        return copy.deepcopy(new)
    if not new:
        return out

    for key, value in new.items():
        if key == "horses":
            out["horses"] = _merge_horses(out.get("horses"), value)
            continue
        if key == "preparedMeta" and isinstance(value, dict):
            pm = dict(out.get("preparedMeta") or {})
            pm.update(copy.deepcopy(value))
            out["preparedMeta"] = pm
            continue
        if key == "result" and isinstance(value, dict):
            result = dict(out.get("result") or {})
            for rkey, rvalue in value.items():
                if _meaningful(rvalue) or rkey not in result:
                    result[rkey] = copy.deepcopy(rvalue)
            out["result"] = result
            continue
        if _meaningful(value) or key not in out:
            out[key] = copy.deepcopy(value)
    return out


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


def _raw_snapshot(rid: str) -> dict[str, Any] | None:
    detail = app._prepared_get_fresh(rid) or app._racedb_get_fast(rid) or app._fast_local_race_detail(rid)
    return detail if isinstance(detail, dict) else None


def _snapshot(rid: str) -> dict[str, Any] | None:
    detail = _raw_snapshot(rid)
    if not isinstance(detail, dict):
        return None
    try:
        compact = app._compact_display_snapshot(detail)
        return compact if isinstance(compact, dict) else detail
    except Exception:
        return detail


def _seed_snapshot(detail: dict[str, Any] | None) -> None:
    """Best-effort local persistence only; D1 payload correctness must not depend on it."""
    if not isinstance(detail, dict) or not detail.get("id"):
        return
    try:
        app._store_fast_snapshot(copy.deepcopy(detail))
    except Exception as exc:
        print("FULL_PREFETCH_SEED_WARN", detail.get("id"), type(exc).__name__, exc)


def _supplement_missing(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    """Search every registered provider before accepting a thin prediction input."""
    if not isinstance(detail, dict) or not detail.get("id"):
        return detail
    if str(os.getenv("ARVEXQ_SUPPLEMENT_MISSING", "1")).strip().lower() in {"0", "false", "off", "no"}:
        return detail
    try:
        return enrich_race_missing_sync(
            detail,
            history_limit=5,
            max_parallel_horses=int(os.getenv("ARVEXQ_SUPPLEMENT_HORSE_WORKERS", "4") or 4),
        )
    except Exception as exc:
        print("FULL_PREFETCH_SUPPLEMENT_WARN", detail.get("id"), type(exc).__name__, exc)
        return detail


def _ensure_analysis(rid: str, current: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str]:
    """Run app.py diagnosis and keep its returned JSON even if SQLite persistence fails."""
    raw_before = _raw_snapshot(rid)
    latest = _merge_detail(current, raw_before)
    if _analysis_current(latest):
        return latest, ""
    if latest:
        _seed_snapshot(latest)

    errors: list[str] = []
    shallow: dict[str, Any] | None = None
    try:
        built = app._build_fast_diagnosis_snapshot(
            rid,
            allow_network=False,
            deep_context=False,
        )
        if isinstance(built, dict) and built.get("id"):
            shallow = built
            # Persist when possible, but never make the returned analysis depend
            # on SQLite/cache success.
            _seed_snapshot(built)
    except Exception as exc:
        errors.append(f"shallow:{type(exc).__name__}:{exc}")

    raw_after_shallow = _raw_snapshot(rid)
    latest = _merge_detail(latest, raw_after_shallow)
    latest = _merge_detail(latest, shallow)
    if _analysis_ready(latest):
        return latest, ";".join(errors)

    # FULL PREFETCH is the heavy lane, so one deep fallback is allowed when the
    # prepared card is not sufficient to produce all-head diagnosis.
    deep: dict[str, Any] | None = None
    try:
        built = app._build_fast_diagnosis_snapshot(
            rid,
            allow_network=True,
            deep_context=True,
        )
        if isinstance(built, dict) and built.get("id"):
            deep = built
            _seed_snapshot(built)
    except Exception as exc:
        errors.append(f"deep:{type(exc).__name__}:{exc}")

    raw_after_deep = _raw_snapshot(rid)
    latest = _merge_detail(latest, raw_after_deep)
    latest = _merge_detail(latest, deep)
    if not _analysis_ready(latest) and not errors:
        errors.append("diagnosis builder completed but diagnosisReady is false")
    return latest or current, ";".join(errors)


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
    # Read-only evidence decoration: no re-ranking, mark update, or post-race analysis.
    return attach_evidence(out)


def prepare(
    bundle_path: str,
    payload_path: str,
    report_path: str,
    workers: int,
    analysis_workers: int,
) -> int:
    bundle = _read(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    initial = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id")]
    by_id: dict[str, dict[str, Any]] = {str(d["id"]): d for d in initial}
    errors: dict[str, str] = {}
    analysis_errors: dict[str, str] = {}
    skipped_unchanged: list[str] = []

    def prepare_card(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        raw = _raw_snapshot(rid)
        current = _merge_detail(by_id.get(rid), raw)
        if _card_usable(current):
            current = _supplement_missing(current)
            return rid, current, ""
        try:
            prepared = app._prepare_race_snapshot(rid, force=True)
            detail = prepared if isinstance(prepared, dict) else None
        except Exception as exc:
            detail = None
            return rid, current or None, f"{type(exc).__name__}: {exc}"
        # If RaceDB save failed, keep the returned prepared card authoritative.
        latest = _merge_detail(current, _raw_snapshot(rid))
        latest = _merge_detail(latest, detail)
        latest = _supplement_missing(latest)
        if latest and latest.get("id"):
            return rid, latest, ""
        return rid, None, "no usable snapshot after card preparation"

    ids = [str(r["id"]) for r in rows]
    card_targets = [rid for rid in ids if not _card_usable(by_id.get(rid))]
    print(f"FULL_PREFETCH cards races={len(ids)} targets={len(card_targets)}")

    if card_targets:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(card_targets)))) as pool:
            futures = {pool.submit(prepare_card, rid): rid for rid in card_targets}
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    _, detail, error = fut.result()
                except Exception as exc:
                    detail, error = None, f"{type(exc).__name__}: {exc}"
                if detail:
                    by_id[rid] = detail
                if error:
                    errors[rid] = error
                    print("FULL_PREFETCH_CARD_WARN", rid, error)

    # Diagnose only cards whose prediction fingerprint is not already current.
    analysis_targets = []
    for rid in ids:
        detail = _merge_detail(by_id.get(rid), _raw_snapshot(rid))
        detail = _supplement_missing(detail)
        if detail:
            by_id[rid] = detail
        if _card_usable(detail):
            if _analysis_current(detail):
                skipped_unchanged.append(rid)
            else:
                analysis_targets.append(rid)

    print(
        f"FULL_PREFETCH analysis targets={len(analysis_targets)} "
        f"unchanged={len(skipped_unchanged)}"
    )
    if analysis_targets:
        # app.py persists into one SQLite RaceDB. Production deliberately uses
        # one diagnosis worker; the merge above keeps returned JSON authoritative
        # even if local persistence is unavailable.
        with ThreadPoolExecutor(
            max_workers=max(1, min(analysis_workers, len(analysis_targets)))
        ) as pool:
            futures = {
                pool.submit(_ensure_analysis, rid, by_id.get(rid)): rid
                for rid in analysis_targets
            }
            for fut in as_completed(futures):
                rid = futures[fut]
                try:
                    detail, error = fut.result()
                except Exception as exc:
                    detail, error = None, f"{type(exc).__name__}: {exc}"
                if detail:
                    by_id[rid] = detail
                if error:
                    analysis_errors[rid] = error
                    print("FULL_PREFETCH_ANALYSIS_WARN", rid, error)

    decorated: dict[str, dict[str, Any]] = {}
    for rid in ids:
        # Local RaceDB can lag if a write was locked/read-only. Never let that
        # stale copy erase the in-memory card/diagnosis we just built.
        detail = _merge_detail(_raw_snapshot(rid), by_id.get(rid))
        if detail.get("id"):
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
            "source": "github-actions-full-prefetch-v4-memory-authoritative",
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
        "card_errors": errors,
        "analysis_errors": analysis_errors,
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
    for rid in missing_analysis:
        print(
            "FULL_PREFETCH_ANALYSIS_MISSING",
            rid,
            analysis_errors.get(rid, "diagnosisReady=false"),
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="bundle.json")
    parser.add_argument("--payload", default="prefetch-payload.json")
    parser.add_argument("--report", default="prefetch-report.json")
    parser.add_argument("--workers", type=int, default=int(os.getenv("ARVEXQ_PREFETCH_WORKERS", "6")))
    parser.add_argument(
        "--analysis-workers",
        type=int,
        default=int(os.getenv("ARVEXQ_PREFETCH_ANALYSIS_WORKERS", "1")),
    )
    args = parser.parse_args()
    # The heavy prefetch lane always registers configured licensed feeds, even
    # when a legacy app startup path skipped optional source registration.
    try:
        connected = register_authorized_history_feeds(source_registry)
        if connected:
            print("AUTHORIZED_HISTORY_FEEDS_ACTIVE", len(connected), sorted(connected))
    except ValueError as exc:
        print("AUTHORIZED_HISTORY_FEEDS_CONFIG_WARN", str(exc))
    try:
        official = register_nar_official_archive(source_registry)
        if official:
            print("NAR_OFFICIAL_CSV_LOADED", "races=", official.race_count,
                  "horses=", sum(len(v) for v in official.by_name.values()))
    except (OSError, ValueError, KeyError) as exc:
        # A corrupt/missing monthly ZIP does not block the race card or other sources.
        print("NAR_OFFICIAL_CSV_WARN", type(exc).__name__, str(exc))
    return prepare(
        args.bundle,
        args.payload,
        args.report,
        args.workers,
        args.analysis_workers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
