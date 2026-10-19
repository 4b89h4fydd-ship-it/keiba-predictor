#!/usr/bin/env python3
"""Score externally witnessed Stage64 forecasts from saved settled D1 facts.

The sole result source is an EXISTING completed main Full Prefetch artifact.
No collection, data-store mutation, result guessing, or production promotion.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arvexq.research.stage63.forward import write_once
from arvexq.research.stage64.circuits import circuit
from arvexq.research.stage64.evaluation import evaluate
from arvexq.research.stage64.protocol import post_at
from arvexq.research.stage64.witness import GitHubArtifacts, read_witness, verify_batch, instant


def settled(detail):
    result = detail.get("result")
    if not isinstance(result, dict):
        return False
    status = str(result.get("status") or detail.get("raceStatus") or "").strip()
    return status in ("確定", "official", "final", "FINAL", "Official", "競走確定")


def payout_from_saved(result, order):
    """Explicit Japanese trifecta payout only; unknown is NOT a zero return."""
    records = result.get("payouts")
    if not isinstance(records, list):
        return None
    rows = [r for r in records if isinstance(r, dict) and
            r.get("kind") in ("3連単", "３連単", "三連単")]
    if not rows:
        return None
    selected = []
    for row in rows:
        combo = row.get("combination") or row.get("combo")
        if not isinstance(combo, str) or not re.fullmatch(r"\d+[-－–→]\d+[-－–→]\d+", combo):
            raise ValueError("unparseable official trifecta combination")
        parts = tuple(int(v) for v in re.split(r"[-－–→]", combo))
        if len(set(parts)) != 3:
            raise ValueError("invalid payoff combination")
        if parts == order:
            amount = row.get("payout", row.get("amount"))
            if isinstance(amount, str) and re.fullmatch(r"[1-9]\d*(?:,\d{3})*", amount.strip()):
                amount = int(amount.strip().replace(",", ""))
            if type(amount) is not int or amount <= 0:
                # Missing/invalid payout never becomes fabricated zero return.
                return None
            selected.append(amount)
    if len(selected) != 1:
        return None
    return [{"order": list(order), "amount": selected[0]}]


def confirmed_label(detail):
    """Construct only one unambiguous 1-2-3 order from saved settled finishers."""
    if not isinstance(detail, dict) or not settled(detail):
        raise ValueError("result not confirmed")
    result = detail["result"]
    finishers = result.get("finishers")
    if not isinstance(finishers, list):
        raise ValueError("confirmed result has no finishers")
    positions = {}
    seen = set()
    for row in finishers:
        if not isinstance(row, dict):
            raise ValueError("invalid finisher")
        position = row.get("finish", row.get("finishPosition"))
        number = row.get("horseNumber")
        # D1 stored official result fields may use decimal strings; accept only
        # exact positive integers, never fuzzy ranks or post-race inference.
        if isinstance(position, str) and re.fullmatch(r"[1-9]\d*", position.strip()):
            position = int(position.strip())
        if isinstance(number, str) and re.fullmatch(r"[1-9]\d*", number.strip()):
            number = int(number.strip())
        if type(position) is not int or type(number) is not int:
            if position in (None, "", "-", "取消", "除外"):
                continue
            raise ValueError("unparseable confirmed rank")
        if number <= 0 or position <= 0 or number in seen:
            raise ValueError("invalid or repeated finisher")
        seen.add(number)
        if position in (1, 2, 3):
            if position in positions:
                raise ValueError("dead heat without official orders")
            positions[position] = number
    if set(positions) != {1, 2, 3}:
        raise ValueError("missing podium or unhandled dead heat")
    order = tuple(positions[n] for n in (1, 2, 3))
    return {"raceId": detail["id"], "date": detail["date"],
            "circuit": circuit(detail), "status": "confirmed",
            "orders": [list(order)], "payouts": payout_from_saved(result, order)}


def assemble_results(batch, saved):
    """Require one confirmed saved detail per frozen race, no result cherry-picking."""
    if not isinstance(saved, dict) or not isinstance(saved.get("details"), list):
        raise ValueError("saved result details missing")
    wanted = set(batch["cohort"])
    found = {}
    for row in saved["details"]:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if rid not in wanted:
            continue
        if rid in found:
            raise ValueError("duplicate saved result detail")
        found[rid] = row
    problems, labels = [], []
    for rid in batch["cohort"]:
        if rid not in found:
            problems.append({"raceId": rid, "reason": "missing-saved-detail"})
            continue
        try:
            labels.append(confirmed_label(found[rid]))
        except (ValueError, KeyError, TypeError) as exc:
            problems.append({"raceId": rid, "reason": str(exc)[:160]})
    return labels, {"frozenRaces": len(wanted), "confirmedRaces": len(labels),
                    "pendingRaces": problems, "allConfirmed": not problems,
                    "officialSourceIndependentlyRefetched": False}


def score(client, *, plan_id, forecast_id, result_id, output, audit):
    verified = verify_batch(client, plan_id, forecast_id)
    batch = verified["batch"]
    saved, source_anchor = read_witness(client, result_id, before=datetime.now(timezone.utc),
                                        source_member="persisted-facts.json")
    source_run = client.run(source_anchor["runId"])
    # Post-race readback is sourced from the existing D1 route, not
    # predictions or a newly introduced collector. Require our own workflow
    # and never accept a foreign/forked result artifact.
    if (source_run.get("name") != "ARVEXQ Stage64 Shadow Research"
            or source_run.get("event") != "workflow_dispatch"
            or source_run.get("head_repository_id") not in (None, 1386943133)):
        raise ValueError("result source must be a dispatched read-only Stage64 workflow")
    # Authenticated GitHub artifact digest alone does not identify its PURPOSE.
    # Require the exact post-race capture artifact name and reject test/forecast
    # bundles smuggled in as a result source.
    result_metadata = client.metadata(result_id)
    expected_name = "arvexq-stage64-confirmed-d1-" + batch["receipts"][0]["snapshot"]["input"]["date"]
    if (not result_metadata.get("name") == expected_name or
            any(receipt["snapshot"]["input"]["date"] != batch["receipts"][0]["snapshot"]["input"]["date"]
                for receipt in batch["receipts"])):
        raise ValueError("result artifact name or race date differs from frozen cohort")
    last_off = max(post_at(r["snapshot"]["input"]) for r in batch["receipts"])
    if instant(source_anchor["serverObservedBy"]) <= last_off:
        raise ValueError("result artifact workflow completed before last post")
    labels, report = assemble_results(batch, saved)
    report.update({"planArtifactId": plan_id, "forecastArtifactId": forecast_id,
                   "resultArtifactId": result_id, "resultDigest": source_anchor["artifactDigest"],
                   "preoffForecastWitnessVerified": True, "productionChanged": False})
    Path(audit).parent.mkdir(parents=True, exist_ok=True)
    write_once(audit, report)
    if not report["allConfirmed"]:
        print(json.dumps(report, ensure_ascii=False))
        return 2
    evaluated = evaluate(batch, labels, independently_verified=True)
    evaluated["anchors"] = {**verified["anchors"], "result": source_anchor}
    evaluated["resultSourceAuthentication"] = "github-saved-D1-bytes-verified-not-independent-official-refetch"
    evaluated["productionEligible"] = False
    write_once(output, evaluated)
    print(json.dumps({"byCircuit": evaluated["byCircuit"], "researchOnly": True,
                      "productionChanged": False}, ensure_ascii=False))
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan-artifact", required=True, type=int)
    p.add_argument("--forecast-artifact", required=True, type=int)
    p.add_argument("--result-artifact", required=True, type=int)
    p.add_argument("--output", required=True)
    p.add_argument("--audit", required=True)
    a = p.parse_args()
    raise SystemExit(score(GitHubArtifacts(), plan_id=a.plan_artifact,
                           forecast_id=a.forecast_artifact, result_id=a.result_artifact,
                           output=a.output, audit=a.audit))


if __name__ == "__main__":
    main()
