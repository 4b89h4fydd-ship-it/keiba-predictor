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
from arvexq.prediction.career_readiness import assess_career_readiness, attach_career_readiness
from arvexq.prediction.observed_model import model_version
from arvexq.prediction.race_intelligence import attach_evidence
from arvexq.ingest.fallback_enrichment import enrich_race_missing_sync
from arvexq.ingest.full_career import merge_career
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


def _merge_horses(base: Any, fresh: Any, cutoff: str = "") -> list[dict[str, Any]]:
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
            if key in ("recentRaces", "allPastRuns") and isinstance(value, list) and cutoff:
                union = merge_career([*(row.get("allPastRuns") or []), *(row.get("recentRaces") or [])], value, cutoff)
                if union:
                    row["allPastRuns"] = union
                    row["recentRaces"] = union[:5]
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
            out["horses"] = _merge_horses(out.get("horses"), value, str(out.get("date") or new.get("date") or ""))
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
    expected = detail.get("fieldSize") or detail.get("runnerCount") or 0
    try:
        expected = int(expected)
    except (ValueError, TypeError):
        expected = 0
    # A cached two-runner fragment is NOT a finished field of twelve.
    # Include declared scratches in roster cardinality; they are still
    # listed runners but remain unselectable in the client.
    roster = {int(h.get("horseNumber") or 0) for h in (detail.get("horses") or [])
              if isinstance(h, dict) and str(h.get("horseNumber") or "").isdigit()}
    if expected >= 2 and len(roster - {0}) < expected:
        return False
    return core >= max(1, (len(active) * 7 + 9) // 10)


def _recover_existing_racecards(date: str) -> dict[str, dict[str, Any]]:
    """Reuse this same pipeline's previously verified published roster cache.

    No second fetcher: the immutable static racecard is a materialized output
    of an earlier successful official prefetch. It can fill gaps in current
    network responses without ever fabricating horses or replacing richer
    provider observations.
    """
    if not date or len(date) != 10 or date[4] != "-" or date[7] != "-":
        return {}
    path = Path("arvexq/ui/static/racecards") / (date + ".json")
    record = _read(str(path))
    if str(record.get("date") or "") != date:
        return {}
    recovered: dict[str, dict[str, Any]] = {}
    for row in record.get("races") or []:
        if not isinstance(row, dict) or str(row.get("date") or "") != date:
            continue
        if _card_usable(row):
            recovered[str(row["id"])] = row
    return recovered


from arvexq.features.readiness import diagnosis_ready as _analysis_ready


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
            history_limit=max(6, int(os.getenv("ARVEXQ_CAREER_FETCH_LIMIT", "1000"))),
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

    # The AI stage must never acquire missing histories after fact persistence.
    if not errors:
        errors.append("stored evidence insufficient for diagnosis")
    return latest or current, ";".join(errors)



def _enrich_cards_concurrently(cards: dict[str, dict[str, Any]], workers: int = 3) -> dict[str, dict[str, Any]]:
    """Isolate network-only lifetime enrichment from SQLite-backed AI diagnosis.

    Each input is a separate race snapshot. No worker persists a RaceDB row,
    so provider I/O can overlap without concurrent prediction/SQLite writers.
    Failures never discard the original racecard or turn missing history into
    a verified zero-start history.
    """
    if not cards:
        return {}
    limit = max(1, min(4, int(workers), len(cards)))
    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=limit) as pool:
        futures = {pool.submit(_supplement_missing, copy.deepcopy(card)): rid
                   for rid, card in cards.items()}
        for future in as_completed(futures):
            rid = futures[future]
            try:
                enriched = future.result()
                results[rid] = _merge_detail(cards[rid], enriched) if isinstance(enriched, dict) else cards[rid]
            except Exception as exc:
                print("FULL_PREFETCH_ENRICH_WARN", rid, type(exc).__name__, exc, flush=True)
                results[rid] = cards[rid]
            print("FULL_PREFETCH_ENRICH_DONE", rid, flush=True)
    return results


def _decorate(detail: dict[str, Any], *, include_evidence: bool = True) -> dict[str, Any]:
    out = copy.deepcopy(detail)
    attach_career_readiness(out)
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
    # Collection stays source-only; attach computed evidence only after a
    # verified D1 readback. No new marks, rankings, or scores before storage.
    return attach_evidence(out) if include_evidence else out


def prepare(
    bundle_path: str,
    payload_path: str,
    report_path: str,
    workers: int,
    analysis_workers: int,
    phase: str = "collect",
) -> int:
    if phase == "analyze":
        return analyze_persisted(bundle_path, payload_path, report_path)
    if phase != "collect":
        raise ValueError("unknown prefetch stage")
    bundle = _read(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id") and str(r.get("track") or "") not in ("帯広", "帯広ば") and "-帯広-" not in str(r.get("id")) and "-帯広ば-" not in str(r.get("id"))]
    initial = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id") and str(d.get("track") or "") not in ("帯広", "帯広ば") and not any(f"-{name}-" in str(d.get("id")) for name in ("帯広", "帯広ば"))]
    by_id: dict[str, dict[str, Any]] = {str(d["id"]): d for d in initial}
    # Replay only validated existing outputs of this SAME canonical prefetch,
    # so a failed upstream HTTP fetch cannot erase a known published roster.
    static = _recover_existing_racecards(str(bundle.get("date") or ""))
    recovered_rosters = []
    for summary in rows:
        rid = str(summary["id"])
        prior = by_id.get(rid)
        prepared = _merge_detail(prior, summary)
        if not _card_usable(prepared) and rid in static:
            prepared = _merge_detail(static[rid], prepared)
            recovered_rosters.append(rid)
        by_id[rid] = prepared
    errors: dict[str, str] = {}
    analysis_errors: dict[str, str] = {}
    skipped_unchanged: list[str] = []

    def prepare_card(rid: str) -> tuple[str, dict[str, Any] | None, str]:
        raw = _raw_snapshot(rid)
        current = _merge_detail(by_id.get(rid), raw)
        if _card_usable(current):
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

    # Build each raw card once, enrich lifetime records with bounded network
    # concurrency, then keep AI/SQLite diagnosis serialized as before.
    inputs = {}
    for rid in ids:
        detail = _merge_detail(by_id.get(rid), _raw_snapshot(rid))
        if isinstance(detail, dict) and detail.get("id"):
            inputs[rid] = detail
    enrichment_workers = int(os.getenv("ARVEXQ_PREFETCH_ENRICH_WORKERS", "3") or 3)
    print(f"FULL_PREFETCH enrichment cards={len(inputs)} workers={min(4, max(1, enrichment_workers))}", flush=True)
    enriched = _enrich_cards_concurrently(inputs, enrichment_workers)
    # Collection ends here. Never call diagnosis, evaluation or ticket builders
    # before verified D1 persistence. Preserve acquired cards in memory on DB lag.
    for rid in ids:
        detail = enriched.get(rid, inputs.get(rid))
        if detail:
            by_id[rid] = detail

    decorated: dict[str, dict[str, Any]] = {}
    for rid in ids:
        # Local RaceDB can lag if a write was locked/read-only. Never let that
        # stale copy erase the in-memory card/diagnosis we just built.
        detail = _merge_detail(_raw_snapshot(rid), by_id.get(rid))
        if detail.get("id"):
            decorated[rid] = _decorate(detail, include_evidence=False)

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
            "source": "github-actions-facts-first-v1",
            "sync_date": bundle.get("date") or "",
            "race_count": len(ids),
            "detail_count": len(decorated),
            "card_complete_count": card_count,
            "reused_verified_rosters": len(recovered_rosters),
            "analysis_count": analysis_count,
            "analysis_skipped_unchanged_count": len(set(skipped_unchanged)),
            "missing_card_count": len(missing_card),
            "missing_analysis_count": len(missing_analysis),
            "display_complete": bool(ids) and not missing_card,
            "analysis_complete": False,
            "pipeline_stage": "facts_stored_pending_d1",
            "prefetched_at": int(datetime.now(JST).timestamp()),
        },
    }
    report = {
        "date": bundle.get("date") or "",
        "races": len(ids),
        "details": len(decorated),
        "cards_ready": card_count,
        "reused_verified_rosters": sorted(recovered_rosters),
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



def _attach_new_method_products(detail: dict[str, Any]) -> dict[str, Any]:
    """Publish the three-analysis prediction through the existing projection without touching stored facts.

    Prefetch D1 payloads previously bypassed public_race, unlike HTTP snapshots.
    Keep the original D1 record (including sealed pre-off archives and every
    career observation); only attach the approved server-computed product fields.
    A blocked/incomplete forecast must never become a synthetic prediction.
    """
    from arvexq.forecast.publication import public_race
    published = public_race(detail)
    if published.get("predictionStatus") != "ready":
        return detail
    result = copy.deepcopy(detail)
    for key in ("predictionStatus", "predictionModelVersion", "prediction",
                "predictionMarks", "recommendedBets"):
        result[key] = copy.deepcopy(published[key])
    return result


def analyze_persisted(bundle_path: str, payload_path: str, report_path: str) -> int:
    """Analyze D1 readback only, via the SAME diagnosis engine as before.

    No racecard/history source is called by this stage. Missing facts stay
    missing and are never turned into fake zero-valued ability marks.
    """
    from arvexq.pipeline.persisted_inputs import verify_persisted_facts, may_create_prerace_prediction
    day = _read(bundle_path)
    rows = [r for r in (day.get("races") or []) if isinstance(r, dict) and r.get("id") and str(r.get("track") or "") not in ("帯広", "帯広ば") and "-帯広-" not in str(r.get("id")) and "-帯広ば-" not in str(r.get("id"))]
    details = {str(d["id"]): d for d in (day.get("details") or [])
               if isinstance(d, dict) and d.get("id")}
    saved = {"races": rows, "details": list(details.values())}
    integrity = verify_persisted_facts(
        {"summaries": rows, "details": list(details.values())}, saved
    )
    if integrity:
        raise ValueError("D1 race identity invalid: " + str(integrity[:8]))
    errors: dict[str, str] = {}
    analyzed: dict[str, dict[str, Any]] = {}
    skipped = []
    for row in rows:
        rid = str(row["id"])
        fact = details.get(rid)
        if not _card_usable(fact):
            errors[rid] = "saved D1 racecard incomplete"
            if fact:
                analyzed[rid] = fact
            continue
        if _analysis_current(fact):
            analyzed[rid] = fact
            skipped.append(rid)
            continue
        if not may_create_prerace_prediction(fact):
            analyzed[rid] = fact
            errors[rid] = "scheduled off passed: no new retrospective pre-race prediction"
            continue
        # Seed just the independently verified D1 detail. Do not call
        # _prepare_race_snapshot or any provider to fill an empty D1 race.
        _seed_snapshot(fact)
        locally_stored = _raw_snapshot(rid)
        if not isinstance(locally_stored, dict):
            errors[rid] = "D1 facts could not be staged in local RaceDB"
            analyzed[rid] = fact
            continue
        stored_check = verify_persisted_facts(
            {"summaries": [row], "details": [fact]},
            {"races": [row], "details": [locally_stored]},
        )
        if stored_check:
            errors[rid] = "RaceDB staging mismatch: " + ";".join(stored_check[:3])
            analyzed[rid] = fact
            continue
        try:
            # Explicitly disables the previous deep network fallback.
            predicted, err = _ensure_analysis(rid, fact)
            final = _decorate(_merge_detail(fact, predicted)) if isinstance(predicted, dict) else fact
            if _analysis_ready(final):
                # Observed D1 runner identities and all prior history are immutable.
                after = verify_persisted_facts(
                    {"summaries": [row], "details": [fact]},
                    {"races": [row], "details": [final]},
                )
                if after:
                    errors[rid] = "diagnosis modified saved facts: " + ";".join(after[:3])
                    analyzed[rid] = fact
                else:
                    analyzed[rid] = final
                    if err:
                        print("PERSISTED_DIAGNOSIS_WARN", rid, err)
            else:
                analyzed[rid] = fact
                errors[rid] = err or "stored evidence not adequate for diagnosis"
        except Exception as exc:
            analyzed[rid] = fact
            errors[rid] = f"{type(exc).__name__}: {exc}"
    # An existing diagnosis flag does not attest to a calibrated new-method product.
    # Attach only products actually computed from the read-back, pre-off facts.
    from arvexq.pipeline.persisted_inputs import may_create_prerace_prediction
    eligible = 0
    products_ready = 0
    for rid, detail in list(analyzed.items()):
        if not may_create_prerace_prediction(detail):
            continue
        eligible += 1
        published = _attach_new_method_products(detail)
        if published.get("predictionStatus") == "ready" and published.get("predictionMarks"):
            analyzed[rid] = published
            products_ready += 1
    print("PERSISTED_D1_NEW_METHOD_PRODUCTS", "preoff=", eligible, "ready=", products_ready)
    payload = {
        "summaries": rows,
        "details": [analyzed[str(r["id"])] for r in rows if str(r["id"]) in analyzed],
        "meta": {
            "source": "github-actions-persisted-d1-analysis-v1",
            "pipeline_stage": "predictions_pending_d1",
            "sync_date": day.get("date") or "",
            "race_count": len(rows),
            "detail_count": len(analyzed),
            "analysis_count": sum(1 for x in analyzed.values() if _analysis_ready(x)),
            "missing_card_count": sum(1 for rid in errors if errors[rid].startswith("saved D1")),
            "missing_analysis_count": len(errors),
            "analysis_missing_count": len(errors),
            "display_complete": len(analyzed) == len(rows) and all(_card_usable(x) for x in analyzed.values()),
            "analysis_complete": bool(rows) and not errors,
        },
    }
    _write(payload_path, payload)
    _write(report_path, {
        "date": day.get("date") or "",
        "races": len(rows),
        "analysis_ready": payload["meta"]["analysis_count"],
        "unchanged": skipped,
        "analysis_errors": errors,
        "card_errors": {},
        "missing_analysis": sorted(errors),
        "missing_card": [rid for rid in errors if errors[rid].startswith("saved D1")],
    })
    print("PERSISTED_D1_ANALYSIS", "races=",len(rows),
          "ready=",payload["meta"]["analysis_count"], "missing=",len(errors))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="bundle.json")
    parser.add_argument("--phase", choices=("collect", "analyze"), default="collect")
    parser.add_argument("--payload", default="prefetch-payload.json")
    parser.add_argument("--report", default="prefetch-report.json")
    parser.add_argument("--workers", type=int, default=int(os.getenv("ARVEXQ_PREFETCH_WORKERS", "6")))
    parser.add_argument(
        "--analysis-workers",
        type=int,
        default=int(os.getenv("ARVEXQ_PREFETCH_ANALYSIS_WORKERS", "1")),
    )
    args = parser.parse_args()
    # Each Actions stage is a separate process. Only the collector may talk
    # to existing acquisition providers; the analyzer uses persisted facts.
    if args.phase == "collect":
        os.environ["ARVEXQ_COLLECT_ONLY"] = "1"
    elif args.phase == "analyze":
        os.environ["ARVEXQ_COLLECT_ONLY"] = "0"
        os.environ["ARVEXQ_SUPPLEMENT_MISSING"] = "0"
        os.environ["RACEDB_FULL_HISTORY"] = "0"
        # Analysis does not register data providers or discover racecards.
        return prepare(args.bundle, args.payload, args.report,
                       args.workers, args.analysis_workers, phase="analyze")
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
        phase=args.phase,
    )


if __name__ == "__main__":
    raise SystemExit(main())
