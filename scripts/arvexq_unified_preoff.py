#!/usr/bin/env python3
"""Produce real per-race pre-off unified reference forecasts directly from D1.

This *independent* lane does not wait for all-day prefetch and its unrelated
race-history verification to succeed. It reads earlier finalized real races
for each circuit and family, fits one shared model per family, and persists
time-stamped, one-source marks/pace/ticket-status to each still-upcoming race.

No current/post-off race is ever scored and no race results/odds are invented.
Existing genuinely sealed predictions are never replaced. No banei.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.learned_scenarios import fit_model, race_family
from arvexq.prediction.prerace_archive import JST, post_at, sealed_lock
from arvexq.prediction.unified_product import generate, verified
from arvexq.forecast.engine import _has_result_evidence
from scripts.arvexq_kikka_urgent import VALID_BASE, day_summary, race_detail


def _run(*args):
    subprocess.run([sys.executable, *args], check=True, cwd=ROOT, timeout=180)


def _training(base, target_date, needed, *, days=16, max_per_group=35):
    """Bounded D1 history; strictly earlier completed races only."""
    cache = defaultdict(list)
    found = {key: 0 for key in needed}
    failures = []
    day0 = datetime.fromisoformat(target_date).date()
    for offset in range(1, days + 1):
        if all(n >= max_per_group for n in found.values()):
            break
        day = (day0 - timedelta(days=offset)).isoformat()
        try:
            rows = day_summary(base, day)
        except Exception as exc:
            failures.append({"date": day, "errorType": type(exc).__name__})
            continue
        for summary in sorted(rows, key=lambda r: str(r.get("id"))):
            circuit = summary.get("circuit")
            if circuit not in ("中央", "地方"):
                continue
            if any(w in str(summary.get("track") or summary.get("id") or "")
                   for w in ("帯広", "ばんえい")):
                continue
            likely_family = race_family(summary)
            eligible = [key for key in needed if key[0] == circuit and key[1] == likely_family]
            if not eligible or all(found[key] >= max_per_group for key in eligible):
                continue
            try:
                detail = race_detail(base, summary["id"])
            except (ValueError, RuntimeError, KeyError, TimeoutError):
                continue
            key = (detail.get("circuit"), race_family(detail))
            if key not in found or found[key] >= max_per_group:
                continue
            if detail.get("date", "9999") >= target_date:
                continue
            if (detail.get("result") or {}).get("status") != "確定":
                continue
            if len(detail.get("horses") or []) < 3:
                continue
            cache[key].append(detail)
            found[key] += 1
    return cache, failures


def run(base, target_date, *, publish=False, max_races=70,
        now=None, archive_dir=None):
    if base.rstrip("/") != VALID_BASE:
        raise ValueError("unknown API base")
    now = now or datetime.now(JST)
    if now.tzinfo is None:
        raise ValueError("timezone-aware current clock required")
    today = now.astimezone(JST).date().isoformat()
    if target_date < today or target_date > (now.astimezone(JST).date() + timedelta(days=1)).isoformat():
        raise ValueError("only today's or tomorrow's cards, never historical races")
    if type(max_races) is not int or not 1 <= max_races <= 150:
        raise ValueError("bounded race count required")
    summaries = day_summary(base, target_date)
    # Reuse the established provider-enrichment path for missing histories.
    # This is read/enrichment only; it never fabricates runs and never writes
    # D1. If every registered provider is missing, the race remains blocked.
    from scripts.arvexq_prefetch import _supplement_missing
    source, errors, pending = [], [], []
    for summary in summaries:
        if len(pending) >= max_races:
            break
        if summary.get("circuit") not in ("中央", "地方"):
            continue
        if any(token in str(summary.get("track") or summary.get("id") or "")
               for token in ("帯広", "ばんえい")):
            continue
        try:
            row = _supplement_missing(race_detail(base, summary["id"]))
            if (row.get("id") != summary["id"] or row.get("date") != target_date
                    or row.get("circuit") != summary.get("circuit")
                    or not row.get("horses") or _has_result_evidence(row.get("result"))):
                continue
            off = post_at(row)
            if off is None or now.astimezone(JST) >= off:
                continue
            if sealed_lock(row) or verified(row):
                continue
            pending.append(row)
        except (ValueError, RuntimeError, KeyError, TimeoutError) as exc:
            errors.append({"raceId": summary.get("id"), "reason": type(exc).__name__})
    needed = {(r["circuit"], race_family(r)) for r in pending}
    histories, training_failures = _training(base, target_date, needed) if needed else ({}, [])
    models = {}
    for circuit, family in sorted(needed):
        subset = histories.get((circuit, family), [])
        if not subset:
            errors.append({"circuit": circuit, "family": family, "reason": "no-earlier-finalized-races"})
            continue
        try:
            models[(circuit, family, False)] = fit_model(
                subset, circuit=circuit, family=family, epochs=60)
        except (ValueError, TypeError) as exc:
            errors.append({"circuit": circuit, "family": family, "reason": str(exc)[:150]})
    if any("新馬" in str(r.get("title") or "") for r in pending):
        for circuit, family in needed:
            if family != "flat":
                continue
            try:
                models[(circuit, family, True)] = fit_model(
                    histories[(circuit, family)], circuit=circuit,
                    family="flat", allow_missing_starts=True, epochs=60)
            except (ValueError, KeyError, TypeError):
                pass
    for row in pending:
        debut = "新馬" in str(row.get("title") or "")
        key = (row["circuit"], race_family(row), debut)
        model = models.get(key)
        if model is None:
            errors.append({"raceId": row["id"], "reason": "family-model-not-trained"})
            continue
        try:
            product = generate(row, model, now=datetime.now(JST))
            if verified(dict(row, unifiedForecast=product)) is None:
                raise ValueError("generated receipt fails verification")
            source.append((row, product))
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            errors.append({"raceId": row["id"], "reason": str(exc)[:180]})
    confirmed = []
    if publish and source:
        if not os.environ.get("SYNC_TOKEN"):
            raise ValueError("SYNC_TOKEN missing")
        # Independent one-race transactions. One damaged NAR history should
        # never prevent a different valid racing card's forecast from saving.
        for row, product in source:
            try:
                if datetime.now(JST) >= post_at(row):
                    raise ValueError("off time crossed before D1 guard")
                live = race_detail(base, row["id"])
                if live.get("date") != target_date or _has_result_evidence(live.get("result")):
                    raise ValueError("race changed / already ended")
                if sealed_lock(live) or verified(live):
                    continue
                if {h["horseNumber"]: h.get("name") for h in live["horses"]} != {
                    h["horseNumber"]: h.get("name") for h in row["horses"]}:
                    raise ValueError("roster changed since forecast")
                updated = dict(live, unifiedForecast=product)
                with tempfile.TemporaryDirectory(prefix="arvexq-unified-") as td:
                    payload = Path(td) / "payload.json"
                    payload.write_text(json.dumps({"summaries": [
                        next(s for s in summaries if s["id"] == row["id"])],
                        "details": [updated], "meta": {"sync_date": target_date,
                        "source": "arvexq-unified-live-v1", "race_count": 1}
                    }, ensure_ascii=False, allow_nan=False), encoding="utf-8")
                    batchdir = Path(td) / "batches"
                    _run("scripts/arvexq_sync_batches.py", "--input",
                         str(payload), "--out-dir", str(batchdir))
                    batches = list(batchdir.glob("batch-*.json"))
                    if len(batches) != 1:
                        raise ValueError("expected exactly one race batch")
                    _run("scripts/arvexq_protect_sync.py", "--file", str(batches[0]),
                         "--api-base", base)
                    _run("scripts/arvexq_d1_capacity_guard.py", "--file", str(batches[0]),
                         "--api-base", base, "--max-bytes", "4000000")
                    _run("scripts/arvexq_protect_sync.py", "--verify-post",
                         "--file", str(batches[0]), "--api-base", base)
                final = race_detail(base, row["id"])
                stored = verified(final)
                if not stored or stored["receiptSha256"] != product["receiptSha256"]:
                    raise ValueError("D1 before-off marks/pace/tickets receipt missing on readback")
                confirmed.append(row["id"])
            except (ValueError, RuntimeError, KeyError, subprocess.CalledProcessError) as exc:
                errors.append({"raceId": row["id"], "reason": str(exc)[:170]})
    report = {
        "version": "arvexq-unified-preoff-runner-v1",
        "date": target_date, "foundCards": len(summaries),
        "eligibleUpcoming": len(pending),
        "scored": len(source), "persistedAndVerified": len(confirmed),
        "circuitFamilyModels": sorted([c + ":" + f for c, f, _ in models]),
        "missingOrSkipped": errors[:100],
        "trainingReadFailures": training_failures[:30],
        "raceIds": [r["id"] for r, _ in source],
        "publishedIds": confirmed,
        "marksFromSameModel": True,
        "historicalForecastsBackfilled": False,
        "oddsWithoutProvenanceUsed": False,
    }
    return report


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD, default next day after 17 JST")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--publish", action="store_true")
    args = p.parse_args(argv)
    at = datetime.now(JST)
    target = args.date or (at.date()+timedelta(days=1) if at.hour>=17 else at.date()).isoformat()
    try:
        report = run(VALID_BASE, target, publish=args.publish)
        status = 0
    except Exception as exc:
        report = {"version": "arvexq-unified-preoff-runner-v1", "date": target,
                  "failed": type(exc).__name__ + ": " + str(exc)[:170]}
        status = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
