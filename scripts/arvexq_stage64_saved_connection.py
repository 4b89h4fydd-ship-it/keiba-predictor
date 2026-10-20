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


def compare_archived_coverage(report: dict, archived: list) -> dict:
    """Compare all three saved-data arms to prior baseline STATUS evidence.

    Archived coverage contains only baseline stages/blockers, not predictions,
    the original 527R input, or source snapshots' hashes. A status match is
    never claimed as full numerical/forecast equivalence.
    """
    if not isinstance(archived, list):
        raise ValueError("archived coverage must be a list")
    indexed = {}
    for item in archived:
        if not isinstance(item, dict) or not isinstance(item.get("raceId"), str):
            raise ValueError("invalid archived coverage row")
        rid = item["raceId"]
        if rid in indexed:
            raise ValueError("duplicate archived race identity")
        indexed[rid] = item
    summary = {owner: {"overlappingRaces": 0, "statusMatchedRaces": 0,
                       "blockersMatchedRaces": 0, "fullyMatchedRaces": 0,
                       "disagreedRaces": 0, "notInArchivedResearch": 0}
               for owner in ("jra", "nar")}
    differences = []
    for row in report["raceRows"]:
        rid, owner = row["raceId"], row["circuit"]
        source = indexed.get(rid)
        if source is None:
            summary[owner]["notInArchivedResearch"] += 1
            continue
        if source.get("circuit") != owner or source.get("date") != row["date"]:
            raise ValueError("archived coverage circuit/date identity conflict")
        expected_stages = source.get("stageStatus")
        expected_blockers = source.get("blockers")
        if not isinstance(expected_stages, dict) or not isinstance(expected_blockers, list):
            raise ValueError("archived stage or blocker evidence invalid")
        arm_differences = {}
        status_match_all, blocker_match_all = True, True
        for arm in ARMS:
            p = row["predictions"][arm]
            observed_status = {k: v["status"] for k, v in p["stages"].items()}
            status_match = observed_status == expected_stages
            # Multiset comparison retains per-run duplicate blocker observations.
            normalized = lambda xs: sorted(json.dumps(x, ensure_ascii=False,
                                                       sort_keys=True) for x in xs)
            blocker_match = normalized(p["blockers"]) == normalized(expected_blockers)
            status_match_all &= status_match
            blocker_match_all &= blocker_match
            if not status_match or not blocker_match:
                arm_differences[arm] = {
                    "stageStatusMatches": status_match,
                    "blockersMatch": blocker_match,
                    "observedStatuses": observed_status if not status_match else None,
                    "archivedStatuses": expected_stages if not status_match else None,
                    "observedBlockers": p["blockers"] if not blocker_match else None,
                    "archivedBlockers": expected_blockers if not blocker_match else None,
                }
        totals = summary[owner]
        totals["overlappingRaces"] += 1
        totals["statusMatchedRaces"] += int(status_match_all)
        totals["blockersMatchedRaces"] += int(blocker_match_all)
        totals["fullyMatchedRaces"] += int(status_match_all and blocker_match_all)
        totals["disagreedRaces"] += int(not (status_match_all and blocker_match_all))
        if arm_differences:
            differences.append({"raceId": rid, "circuit": owner,
                                "armDifferences": arm_differences})
    return {
        "schema": "arvexq-stage64-archived-coverage-comparison-1",
        "reference": "existing-stage64-527R-baseline-coverage-not-original-input",
        "byCircuit": summary, "differences": differences,
        "sameRaceIdCoverageCompared": True,
        "sameInputByteEqualityVerified": False,
        "probabilityOrTicketNumericalEqualityVerified": False,
        "independentlyVerifiedPreoff": False,
        "productionEligible": False,
    }


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
        # Diagnostic-only outcome of the existing fixed evidence gate.
        # No blocked race is dropped, no missing history is imputed.
        if len({v["sixStageCalculated"] for v in predictions.values()}) != 1:
            raise ValueError("ability variants diverged on six-stage eligibility")
        if not predictions[ARMS[0]]["sixStageCalculated"]:
            reasons = {b["reason"] for b in predictions[ARMS[0]]["blockers"]}
            if "unsupported-discipline" in reasons:
                metrics[owner]["blockedUnsupportedDisciplineRaces"] += 1
            elif "no-valid-finish-history" in reasons or "no-valid-corner-history" in reasons:
                metrics[owner]["blockedInsufficientHistoryRaces"] += 1
            else:
                metrics[owner]["blockedOtherRaces"] += 1
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
    parser.add_argument("--compare-coverage", type=Path,
                        help="Existing Stage64 coverage.json, read-only; same-race status comparison")
    a = parser.parse_args()
    report = run_saved_day(a.date, root=a.archive_dir)
    if a.compare_coverage is not None:
        archived = json.loads(a.compare_coverage.read_text(encoding="utf-8"))
        report["archivedCoverageComparison"] = compare_archived_coverage(report, archived)
    # Write once ONLY to a new research artifact; never edit saved originals.
    write_once(a.output, report)
    print("STAGE64_SAVED_TRIAL=" + json.dumps({
        "date": report["date"], "byCircuit": report["byCircuit"],
        "productionEligible": report["productionEligible"],
        "independentlyVerifiedPreoff": report["independentlyVerifiedPreoff"],
        "historical527Comparison": report["historical527Comparison"],
        "archivedCoverageByCircuit": report.get("archivedCoverageComparison", {}).get("byCircuit"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
