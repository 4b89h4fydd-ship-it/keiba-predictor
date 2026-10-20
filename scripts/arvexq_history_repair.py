#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repair only missing fields in one historical ARVEXQ day.

A rich D1 snapshot is the base. Complete cards are never rebuilt merely to get a
missing result/payout; only incomplete cards use the heavier race preparation.
"""
from __future__ import annotations

import argparse
import asyncio
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
        # Prefer the richer roster, but never erase earlier dated career runs.
        source_horses = {int(h.get("horseNumber") or 0):h
                         for h in old.get("horses") or [] if isinstance(h,dict)}
        roster = copy.deepcopy(new.get("horses") or [])
        from arvexq.ingest.full_career import merge_career
        cutoff = str(out.get("date") or "")
        for horse in roster:
            if not isinstance(horse,dict):
                continue
            prior = source_horses.get(int(horse.get("horseNumber") or 0),{})
            union = merge_career([*(prior.get("allPastRuns") or []),*(prior.get("recentRaces") or [])],
                                 [*(horse.get("allPastRuns") or []),*(horse.get("recentRaces") or [])],cutoff)
            if union:
                horse["allPastRuns"] = union
                horse["recentRaces"] = union[:5]
        out["horses"] = roster
        for key in ("fieldSize", "title", "surface", "distance", "weather", "condition"):
            value = new.get(key)
            if value not in (None, "", 0, "不明"):
                out[key] = copy.deepcopy(value)
    return out


def select_publication_ids(ids: list[str], by_id: dict[str, dict],
                           changed_ids: set[str], initial_publication: bool = False) -> list[str]:
    """Publish all existing source originals only when D1 day was confirmed empty."""
    publish = list(ids) if initial_publication else [rid for rid in ids if rid in changed_ids]
    if initial_publication:
        missing = [rid for rid in publish if not isinstance(by_id.get(rid), dict)
                   or str(by_id[rid].get("id") or "") != rid]
        if missing:
            raise ValueError("cold-start source details missing: " + ",".join(missing[:12]))
    return publish


def repair(bundle_path: str, payload_path: str, report_path: str, workers: int, central_margins_only: bool = False, initial_publication: bool = False) -> int:
    bundle = read_json(bundle_path)
    rows = [r for r in (bundle.get("races") or []) if isinstance(r, dict) and r.get("id")]
    details = [d for d in (bundle.get("details") or []) if isinstance(d, dict) and d.get("id")]
    if central_margins_only:
        rows = [r for r in rows if r.get("circuit") in ("JRA", "中央")]
        details = [d for d in details if d.get("circuit") in ("JRA", "中央")]
    by_id = {str(d["id"]): d for d in details}
    row_by_id = {str(r["id"]): r for r in rows}
    ids = [str(r["id"]) for r in rows]
    errors: dict[str, str] = {}
    result_only_repairs = 0
    card_repairs = 0
    changed_ids: set[str] = set()

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
        pending = [] if central_margins_only else pending_ids()
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
                    original = by_id.get(rid)
                    merged = merge_history(original, fresh)
                    if merged != original:
                        by_id[rid] = merged
                        changed_ids.add(rid)
                        _seed_base(rid, merged)
                        if mode == "result":
                            result_only_repairs += 1
                        elif mode == "card":
                            card_repairs += 1
                    if history_complete(by_id.get(rid)):
                        errors.pop(rid, None)
        if attempt == 1 and pending_ids():
            time.sleep(float(os.getenv("ARVEXQ_HISTORY_RETRY_SLEEP_SEC", "2")))

    # A genuine winner has exactly zero seconds behind the winner.
    # Presence, not truthiness, determines whether the margin was acquired.
    def has_observed_margin(run: dict[str, Any]) -> bool:
        return any(run.get(key) is not None and run.get(key) != ""
                   for key in ("marginText", "marginSeconds", "timeBehindWinner", "margin"))

    # Repair prediction-input history independently of card/result completeness.
    # The prior early exit left complete racecards with empty sectional and
    # margin evidence permanently untouched.
    from arvexq.ingest.fallback_enrichment import enrich_race_missing
    from arvexq.prediction.past_performance import observed_runs
    from arvexq.databanks.registry import DataBankRegistry, registry
    from arvexq.ingest.career_transport import recover_horse
    selected_bank = registry
    if central_margins_only:
        selected_bank = DataBankRegistry()
        selected_bank.register(registry.get("jra_official_prior_results"))
    factor_scanned = factor_changed = 0
    missing_before = missing_after = 0
    max_factor_races = max(1, int(os.getenv("ARVEXQ_FACTOR_BACKFILL_RACES", "2")))
    # Rotate the two-race heavy-fetch window; do not retry the first two
    # incomplete races on every run while starving all other runners.
    offset = max(0, int(os.getenv("ARVEXQ_FACTOR_BACKFILL_OFFSET", "0")))
    rotating_ids = ids[offset % len(ids):] + ids[:offset % len(ids)] if ids else []
    for rid in rotating_ids:
        if factor_scanned >= max_factor_races:
            break
        base = by_id.get(rid)
        if not isinstance(base, dict) or not base.get("horses"):
            continue
        if central_margins_only:
            base = copy.deepcopy(base)
            base["horses"] = [recover_horse(h, base["date"]) for h in base["horses"]]
        horses = active_horses(base)
        incomplete = []
        for horse in horses:
            runs = observed_runs(horse, base, limit=5)
            if not runs:
                incomplete.append(horse)
                continue
            if len(runs) < 5 or any(
                not (run.get("last3fRank") or run.get("last600Rank") or
                     run.get("last3fPercentile") or run.get("last3f") or
                     run.get("last3fSeconds") or run.get("last3FRank"))
                or not has_observed_margin(run)
                for run in runs
            ):
                incomplete.append(horse)
        missing_before += len(incomplete)
        if not incomplete:
            continue
        factor_scanned += 1
        try:
            # Existing registered providers only; keep the original frozen
            # forecasts and tickets unchanged.
            enriched = asyncio.run(enrich_race_missing(
                base, history_limit=200, max_parallel_horses=4,
                bank_registry=selected_bank))
            if central_margins_only and (enriched.get("preparedMeta") or {}).get("supplementalSearch", {}).get("failures"):
                errors[rid] = str(enriched["preparedMeta"]["supplementalSearch"]["failures"])
            if enriched != base:
                by_id[rid] = enriched
                changed_ids.add(rid)
                factor_changed += 1
                if not central_margins_only:
                    _seed_base(rid, enriched)
            print("JRA_MARGIN_RACE_REPAIRED", rid, "changed=", enriched != base, flush=True) if central_margins_only else None
            missing_after += sum(
                1 for h in active_horses(by_id[rid])
                if len(observed_runs(h, by_id[rid], limit=5)) < 5
                or any(not has_observed_margin(q)
                       for q in observed_runs(h, by_id[rid], limit=5))
            )
        except Exception as exc:
            errors[rid] = f"factor-backfill: {type(exc).__name__}: {exc}"
            missing_after += len(incomplete)
    print("HISTORY_FACTOR_BACKFILL", "racesScanned=", factor_scanned,
          "racesChanged=", factor_changed, "horsesMissingBefore=", missing_before,
          "horsesStillMissing=", missing_after)

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

    publication_ids = select_publication_ids(ids, by_id, changed_ids, initial_publication)
    publication_set = set(publication_ids)
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
        if str(z.get("id") or "") in publication_set:
            summaries.append(z)

    # A populated D1 day still receives strictly the changed subset.
    payload_details = [by_id[rid] for rid in publication_ids]
    payload = {
        "summaries": summaries,
        "details": payload_details,
        "meta": {
            "source": "github-actions-history-missing-only-v2",
            "sync_date": bundle.get("date") or (rows[0].get("date") if rows else "") or "",
            "history_window_days": 7,
            "race_count": len(ids),
            "detail_count": len(payload_details),
            "repaired_count": len(changed_ids),
            "repaired_race_ids": [rid for rid in ids if rid in changed_ids],
            "publication_count": len(publication_ids),
            "initial_publication": bool(initial_publication),
            "result_only_repair_count": result_only_repairs,
            "card_repair_count": card_repairs,
            "missing_card_count": len(missing_card),
            "missing_result_count": len(missing_result),
            "missing_payout_count": len(missing_payout),
            "history_complete": bool(ids) and not missing_card and not missing_result and not missing_payout,
            "factor_races_scanned": factor_scanned,
            "factor_races_changed": factor_changed,
            "factor_horses_missing_before": missing_before,
            "factor_horses_missing_after": missing_after,
            "history_repaired_at": int(time.time()),
        },
    }
    report = {
        "date": payload["meta"]["sync_date"],
        "races": len(ids),
        "changed_race_ids": [rid for rid in ids if rid in changed_ids],
        "published_race_ids": publication_ids,
        "initial_publication": bool(initial_publication),
        "unchanged_count": len(ids) - len(changed_ids),
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
        "changed=", len(changed_ids),
        "unchanged=", len(ids) - len(changed_ids),
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
    p.add_argument("--central-margins-only", action="store_true")
    p.add_argument("--initial-publication", action="store_true",
                   help="Only after the original D1 day is explicitly observed empty")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    return repair(args.bundle, args.payload, args.report, args.workers,
                  args.central_margins_only, args.initial_publication)


if __name__ == "__main__":
    raise SystemExit(main())
