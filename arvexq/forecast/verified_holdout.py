"""Audited offline holdout dataset from independently captured pre-off evidence.

Finishing labels are joined AFTER immutable snapshots are verified. No mark,
ticket, payout, odds or result-bearing race detail becomes a model feature.
No accuracy is reported for unverified or insufficient data.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
import sqlite3

from .preoff_evidence_store import read_capture
from .frozen_research_input import from_frozen_snapshot
from .race_softmax_research import chronological_experiment, _split, predict
from .top_three_joint_research import evaluate_orders

CONFIRMED = {"確定", "confirmed"}
MIN_RACES = 100
MIN_HOLDOUT = 20


def _validated_results(raw):
    if not isinstance(raw, list):
        raise ValueError("results must be an independently sourced list")
    indexed = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("invalid result record")
        rid = item.get("raceId")
        if not isinstance(rid, str) or not rid or rid in indexed:
            raise ValueError("missing or duplicate raceId in final results")
        if item.get("status") not in CONFIRMED:
            raise ValueError("non-final result cannot be used for training")
        finishers = item.get("finishers")
        confirmed = item.get("confirmedAtEpoch")
        if type(confirmed) is not int or confirmed <= 0:
            raise ValueError("independent final-result publication timestamp required")
        if not isinstance(finishers, list) or len(finishers) < 3:
            raise ValueError("complete result field required")
        numbers = [x.get("horseNumber") for x in finishers if isinstance(x, dict)]
        ranks = [x.get("finish") for x in finishers if isinstance(x, dict)]
        if (len(numbers) != len(finishers) or any(type(n) is not int or n <= 0 for n in numbers)
                or len(set(numbers)) != len(numbers) or
                any(type(n) is not int for n in ranks) or
                sorted(ranks) != list(range(1, len(finishers) + 1))):
            # Dead heats, non-finishers and ambiguous dispositions need a
            # separate ranking model and must not silently be coerced.
            raise ValueError("strict final ranks and distinct full-field runners required")
        indexed[rid] = item
    return indexed


def build_verified_races(connection: sqlite3.Connection, final_results: list):
    """Return dated full fields and a transparent reason count.

    Select the latest safely stored evidence for a race before joining an
    independently confirmed finish. No claim is made that a local SQLite
    timestamp is independently authenticated; deployment must ensure that.
    """
    results = _validated_results(final_results)
    rows = connection.execute("""
        SELECT capture_id, race_id, captured_at_epoch
        FROM forecast_preoff_evidence
        ORDER BY race_id, captured_at_epoch DESC, capture_id DESC
    """).fetchall()
    chosen = {}
    for cid, rid, epoch in rows:
        chosen.setdefault(rid, cid)
    reasons = Counter()
    records = []
    for rid, cid in sorted(chosen.items()):
        result = results.get(rid)
        if result is None:
            reasons["no_independent_final_result"] += 1
            continue
        try:
            capture = read_capture(connection, cid)
            if result["confirmedAtEpoch"] <= capture["receipt"]["postAtEpoch"]:
                raise ValueError("result confirmed before scheduled post")
            if capture["storedAtEpoch"] >= result["confirmedAtEpoch"]:
                raise ValueError("snapshot storage is not prior to final result")
            race = from_frozen_snapshot(
                capture["snapshot"], capture["receipt"], result["finishers"]
            )
            # Independent result vs immutable roster comparison occurs above.
            records.append(race)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            reasons["invalid_or_inconsistent_snapshot_or_result"] += 1
    reasons["archived_races"] = len(chosen)
    reasons["verified_labelled_races"] = len(records)
    reasons["final_results_without_capture"] = len(set(results) - set(chosen))
    return records, dict(sorted(reasons.items()))


def evaluate_verified_circuits(connection, final_results, *, min_races=MIN_RACES,
                               min_holdout=MIN_HOLDOUT, **train_settings):
    if type(min_races) is not int or min_races < 10 or type(min_holdout) is not int or min_holdout < 2:
        raise ValueError("minimum sample sizes required")
    races, audit = build_verified_races(connection, final_results)
    partitions = {}
    for race in races:
        partitions.setdefault((race["circuit"], race["family"]), []).append(race)
    reports = {}
    for (circuit, family), cases in sorted(partitions.items()):
        key = circuit + "/" + family
        dates = {case["date"] for case in cases}
        if len(cases) < min_races or len(dates) < 5:
            reports[key] = {"eligible": False, "races": len(cases),
                            "dates": len(dates), "reason": "insufficient verified races/dates"}
            continue
        output = chronological_experiment(cases, **train_settings)
        if output["split"]["test"] < min_holdout:
            reports[key] = {"eligible": False, "races": len(cases),
                            "testRaces": output["split"]["test"],
                            "reason": "insufficient unseen holdout sample"}
            continue
        # The original experiment already locks its train/validation/test
        # chronological split. Reuse precisely that split and its train-only
        # model without looking at test labels during fitting.
        _, validation_races, test_races = _split(cases)
        if len(test_races) != output["split"]["test"] or len(validation_races) != output["split"]["validation"]:
            raise ValueError("chronological split drift")
        order_validation = evaluate_orders(
            [predict(output["model"], race) for race in validation_races],
            validation_races)
        order_test = evaluate_orders(
            [predict(output["model"], race) for race in test_races],
            test_races)
        reports[key] = {
            "positionValidation": order_validation,
            "positionTest": order_test,
            "positionMethod": "conditional-order-win-softmax-baseline-not-fitted-second-third",
            "split": output["split"], "validation": output["validation"],
            "test": output["test"], "modelVersion": output["version"],
            "modelHash": output["model"]["modelHash"],
            "productionEligible": False,
        }
    return {"audit": audit, "byCircuitAndFamily": reports,
            "claim80PercentAchieved": False,
            "status": "offline-research-only-no-mark-or-ticket-results"}
