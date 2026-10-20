#!/usr/bin/env python3
"""Read-only retrospective saved-race connection to the EXISTING Stage64 pipeline.

Never use this as prospective freeze, user marks, betting advice or D1 writer.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.research.stage63.forward import write_once
from arvexq.research.stage64.circuits import circuit
from arvexq.research.stage64.pipeline import STAGES, predict
from arvexq.research.stage64.protocol import ARMS, JST, clean_input
from arvexq.v3.audit.snapshot_digest import _restore, verify_one

SAVED = ROOT / "arvexq" / "ui" / "static"


def run_saved_day(day: str, *, root: Path = SAVED) -> dict:
    """Read all sealed race IDs for an existing past day, JRA and NAR separately."""
    day = date.fromisoformat(day).isoformat()
    if day >= datetime.now(JST).date().isoformat():
        raise ValueError("retrospective saved race date required")
    root = Path(root)
    cards = json.loads((root / "racecards" / (day + ".json")).read_text(encoding="utf-8"))
    manifest = json.loads((root / "saved-snapshots" / (day + ".json")).read_text(encoding="utf-8"))
    if cards.get("date") != day or manifest.get("date") != day:
        raise ValueError("saved manifest and racecard date mismatch")
    rows, entries = cards.get("races"), manifest.get("races")
    if not isinstance(rows, list) or not rows or not isinstance(entries, dict):
        raise ValueError("saved cohort unavailable")
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(entries):
        raise ValueError("duplicate, missing or extra saved race identities")

    metrics = {"jra": Counter(), "nar": Counter()}
    reports = []
    for card in sorted(rows, key=lambda row: row["id"]):
        owner = circuit(card)
        rid, entry = card["id"], entries[card["id"]]
        verified = verify_one(root / "saved-snapshots", rid, entry, day=day,
                              circuit=owner, card_horses=card["horses"])
        if verified["status"] != "verified":
            raise ValueError("saved snapshot not verified")
        envelope = json.loads((root / "saved-snapshots" / entry["file"])
                              .read_text(encoding="utf-8"))
        original = _restore(envelope, entry)
        # Existing Stage64 prospective feature whitelist: no target result,
        # payouts, odds, saved product marks/bets or future outcome labels.
        # The immutable *historical* record may already contain official
        # target outcomes. Remove those top-level labels from a throwaway
        # projection BEFORE the existing fail-closed clean_input validator.
        # Never alter or back-write the recovered source original.
        preoff_only = {k: v for k, v in original.items()
                       if k not in ("result", "results", "payouts")}
        features = clean_input(preoff_only)
        if any(k in features for k in ("result", "results", "payouts", "preRaceBet",
                                       "morningMarkSnapshot", "odds", "winOdds")):
            raise ValueError("post-result or product fields in Stage64 input")

        predictions = {}
        for arm in ARMS:
            p = predict(features, expected_circuit=owner, ability_method=arm)
            if p["productionEligible"] is not False or p["independent"] is not False:
                raise ValueError("research stage was unexpectedly promoted")
            if tuple(p["stages"]) != STAGES or p["abilityMethod"] != arm:
                raise ValueError("Stage64 stages/ability arms changed")
            marks, tickets = p["stages"]["marks"]["value"], p["stages"]["tickets"]["value"]
            if marks is not None and marks["productMarks"] is not None:
                raise ValueError("unapproved product marks")
            if tickets is not None and tickets["recommendedBets"] is not None:
                raise ValueError("research tickets promoted to recommendations")
            executable = all(stage["value"] is not None for stage in p["stages"].values())
            metrics[owner]["armsExecuted"] += 1
            metrics[owner]["sixStageCalculated"] += int(executable)
            metrics[owner]["unscoredArms"] += int(not executable)
            predictions[arm] = {
                "abilityMethod": arm, "stages": p["stages"],
                "blockers": p["blockers"],
                "sixStageCalculated": executable, "productionEligible": False,
            }
        metrics[owner]["races"] += 1
        reports.append({"raceId": rid, "date": day, "circuit": owner,
                        "savedSourceSha256": entry["sha256"], "rosterVerified": True,
                        "researchOnly": True, "productionEligible": False,
                        "predictions": predictions})
    if not all(metrics[owner]["races"] for owner in ("jra", "nar")):
        raise ValueError("saved cohort must contain separate JRA/NAR races")
    return {
        "schema": "arvexq-stage64-saved-trial-1",
        "date": day, "source": "existing-static-saved-snapshots-only",
        "byCircuit": {owner: dict(metrics[owner]) for owner in ("jra", "nar")},
        "abilityMethods": list(ARMS), "stages": list(STAGES),
        "raceRows": reports,
        "historical527Comparison": "different-saved-cohort; numerical equivalence not claimed",
        "independentlyVerifiedPreoff": False, "productionEligible": False,
        "productionChanged": False, "productMarks": None, "recommendedBets": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Past saved YYYY-MM-DD")
    parser.add_argument("--archive-dir", type=Path, default=SAVED)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    report = run_saved_day(a.date, root=a.archive_dir)
    # Write once ONLY to a new research artifact; never edit saved originals.
    write_once(a.output, report)
    print("STAGE64_SAVED_TRIAL=" + json.dumps({
        "date": report["date"], "byCircuit": report["byCircuit"],
        "productionEligible": report["productionEligible"],
        "independentlyVerifiedPreoff": report["independentlyVerifiedPreoff"],
        "historical527Comparison": report["historical527Comparison"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
