#!/usr/bin/env python3
"""One-race emergency pre-off D1 read, learned candidate fit and protected publish.

Does not create a Stage64 prediction, does not scrape licensed race videos, and
does not mark unvalidated probabilities/tickets production-ready. The race is
exactly the 2026 Kikuka Sho, all other races (including banei) are skipped.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.prediction.kikka_urgent import (
    RACE_ID, RACE_DATE, verified_entry, compact_candidate,
    overlay_preserving_facts, candidate_marks,
)
from arvexq.prediction.learned_scenarios import fit_model
from arvexq.prediction.prerace_archive import JST
from arvexq.pipeline.persisted_inputs import verify_persisted_facts
from arvexq.ingest.full_snapshot_codec import unpack_detail as unpack_full
from scripts.arvexq_fetch_d1_bundle import get_json, detail_from_response

VALID_BASE = "https://kraiz-api.4b89h4fydd.workers.dev"


def day_summary(base: str, date: str) -> list:
    info = get_json(base + "/api/day?date=" + date + "&details=0&t=" +
                    str(time.time_ns()), 25, 3)
    if info.get("ok") is False or not isinstance(info.get("races"), list):
        raise ValueError("D1 official day summary unavailable")
    if info.get("date") and info.get("date") != date:
        raise ValueError("D1 day date mismatch")
    return [r for r in info["races"] if isinstance(r, dict) and r.get("id")]


def race_detail(base: str, rid: str) -> dict:
    url = base + "/api/race/" + urllib.parse.quote(rid, safe="")
    for suffix in ("?view=display&t=", "?t="):
        try:
            body = get_json(url + suffix + str(time.time_ns()), 25, 2)
            detail = detail_from_response(body, rid)
            if detail:
                return detail
        except RuntimeError:
            continue
    raise ValueError("D1 race detail not available: " + rid)


def training_races(base: str, dates: tuple[str, ...] =
                   ("2026-10-24", "2026-10-18"), max_races: int = 30):
    """Read only earlier JRA race results, never the target day's outcomes."""
    eligible, failures, seen = [], [], set()
    for day in dates:
        if day >= RACE_DATE:
            raise ValueError("training leakage: not earlier than target")
        try:
            summaries = day_summary(base, day)
        except Exception as exc:
            failures.append({"date": day, "reason": type(exc).__name__})
            continue
        rows = sorted((r for r in summaries
                       if r.get("circuit") in ("中央", "jra")
                       and r.get("id") not in seen
                       and r.get("date", day) < RACE_DATE
                       and "-帯広" not in str(r.get("id"))),
                      key=lambda r: str(r["id"]))
        for race in rows:
            if len(eligible) >= max_races:
                break
            rid = str(race["id"])
            seen.add(rid)
            try:
                detail = race_detail(base, rid)
            except Exception:
                continue
            if detail.get("circuit") != "中央":
                continue
            if (detail.get("result") or {}).get("status") != "確定":
                continue
            if not detail.get("horses") or detail.get("date", "9999") >= RACE_DATE:
                continue
            eligible.append(detail)
        if len(eligible) >= max_races:
            break
    return eligible, failures


def _run(*args):
    subprocess.run([sys.executable, *args], check=True,
                   cwd=ROOT, timeout=150)


def build_and_publish(base: str, *, write: bool = False) -> dict:
    if base.rstrip("/") != VALID_BASE:
        raise ValueError("only authorized ARVEXQ D1 endpoint accepted")
    at = datetime.now(JST)
    rows = day_summary(base, RACE_DATE)
    summary = next((r for r in rows if r.get("id") == RACE_ID), None)
    if not summary:
        raise ValueError("Kyoto 11R not in saved official D1 day")
    detail = race_detail(base, RACE_ID)
    verified_entry(detail, summary, at)
    train, source_errors = training_races(base)
    if not train:
        raise ValueError("no earlier D1 JRA finalized race with full runner history")
    model = fit_model(train, circuit="中央", family="flat", epochs=80)
    # Latest upstream market/bodyweight changes cannot be replaced by stale
    # values fetched before the expensive model training.
    latest = race_detail(base, RACE_ID)
    verified_entry(latest, summary, datetime.now(JST))
    candidate = compact_candidate(latest, summary, model, datetime.now(JST))
    prepared = overlay_preserving_facts(
        latest, latest, summary, candidate, datetime.now(JST))
    outcome = {
        "raceId": RACE_ID, "date": RACE_DATE,
        "status": "preoff-learned-candidate-computed",
        "trainedRaces": len(model["training"]["raceIds"]),
        "lastTrainingDate": model["training"]["lastDate"],
        "sourceGaps": source_errors,
        "horses": len(prepared["horses"]),
        "markCount": len(candidate["marks"]),
        "candidateHash": candidate["sourceHash"],
        "productionEligible": False, "ticketsRecommended": False,
        "persistedToD1": False,
    }
    if not write:
        return outcome
    if not os.environ.get("SYNC_TOKEN"):
        raise ValueError("SYNC_TOKEN absent: no production write")
    # Recheck before a D1 write and protect every existing sealed original.
    verified_entry(prepared, summary, datetime.now(JST))
    with tempfile.TemporaryDirectory(prefix="arvexq-kikka-") as td:
        base_path = Path(td)
        payload = base_path / "payload.json"
        payload.write_text(json.dumps({
            "summaries": [summary], "details": [prepared],
            "meta": {"source": "arvexq-kikka-urgent-learned-candidate-v1",
                     "race_count": 1, "sync_date": RACE_DATE}
        }, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        batch_dir = base_path / "batches"
        _run("scripts/arvexq_sync_batches.py", "--input", str(payload),
             "--out-dir", str(batch_dir))
        batches = sorted(batch_dir.glob("batch-*.json"))
        if len(batches) != 1:
            raise ValueError("one-race emergency must emit exactly one guarded D1 batch")
        # The final guarded write still must occur BEFORE the official off.
        verified_entry(prepared, summary, datetime.now(JST))
        def check_prepared_symbols(stage):
            batch = json.loads(batches[0].read_text(encoding="utf-8"))
            full = unpack_full((batch.get("details") or [{}])[0])
            rows = (full.get("kikkaCandidate") or {}).get("marks") or []
            keys = sorted(rows[0]) if rows and isinstance(rows[0], dict) else []
            expected = candidate_marks(prepared)
            actual = candidate_marks(full)
            print("KIKKA_SYMBOL_TRANSPORT", stage, "storedRowKeys=", keys,
                  "verifiedSymbols=", len(actual or []), flush=True)
            if not expected or actual != expected:
                raise ValueError("Kikuka symbols stripped during " + stage)
        check_prepared_symbols("batch-pre-guard")
        _run("scripts/arvexq_protect_sync.py",
             "--file", str(batches[0]), "--api-base", base)
        check_prepared_symbols("batch-post-guard")
        _run("scripts/arvexq_d1_capacity_guard.py",
             "--file", str(batches[0]), "--api-base", base, "--max-bytes", "4000000")
        _run("scripts/arvexq_protect_sync.py", "--verify-post",
             "--file", str(batches[0]), "--api-base", base)
        # Read D1 again. Never equate a successful API response with
        # persisted original facts or with a stored candidate.
        stored = race_detail(base, RACE_ID)
        issues = verify_persisted_facts(
            {"summaries": [summary], "details": [latest]},
            {"races": [summary], "details": [stored]})
        if issues:
            raise ValueError("D1 original observed facts changed: " + ";".join(issues[:3]))
        if (stored.get("kikkaCandidate") or {}).get("sourceHash") != candidate["sourceHash"]:
            raise ValueError("D1 did not persist urgent candidate unchanged")
        # Crucial production contract: source hash can survive while a legacy
        # projection silently removes every literal mark key. Verify the
        # actual restored runner+symbol mapping, not just the model hash.
        expected_marks = candidate_marks(prepared)
        actual_marks = candidate_marks(stored)
        if not expected_marks or actual_marks != expected_marks:
            rows = (stored.get("kikkaCandidate") or {}).get("marks") or []
            keys = sorted(rows[0]) if rows and isinstance(rows[0], dict) else []
            raise ValueError("D1 model hash stored but visible symbols missing or altered; storedMarkKeys=" + ",".join(keys))
        outcome["persistedVisibleMarkCount"] = len(actual_marks)
        outcome["persistedToD1"] = True
        outcome["status"] = "preoff-learned-candidate-persisted"
    return outcome


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--api-base", default=VALID_BASE)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--publish", action="store_true")
    args = p.parse_args(argv)
    try:
        result = build_and_publish(args.api_base, write=args.publish)
    except Exception as exc:
        result = {"raceId": RACE_ID, "status": "failed", "reason":
                  type(exc).__name__ + ": " + str(exc)[:260],
                  "productionEligible": False, "persistedToD1": False}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False))
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
