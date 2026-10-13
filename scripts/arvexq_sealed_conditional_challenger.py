#!/usr/bin/env python3
"""Research-only, leakage-gated conditional race model fitted to sealed pre-off heads.

All predictors originate solely from the ORIGINAL frozen pre-off lock. Official
results enter only as labels. A candidate is chosen using earlier train/validation
dates and reported on held-out later dates. This is archived-model research, NOT
a measurement of the current three-factor production engine. Never writes marks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from scripts.arvexq_integrated_research import (
    eligible, paired_bootstrap, summarize,
)

VERSION = "arvexq-sealed-conditional-rank-challenger-v1"
HEADS = ("decisionProbability", "p1Probability", "p2Probability", "p3Probability")
EPS = 1e-12


def _softmax(logits):
    peak = max(logits)
    values = [math.exp(x - peak) for x in logits]
    total = math.fsum(values)
    return [v / total for v in values]


def _features(race):
    heads = race["heads"]
    if any(heads[k] is None for k in HEADS):
        raise ValueError("missing or invalid frozen probability vector")
    baseline = heads[HEADS[0]]
    other = [heads[k] for k in HEADS[1:]]
    return [[math.log(max(head[i], EPS)) - math.log(max(baseline[i], EPS))
             for head in other] for i in range(len(baseline))]


def predict(race, theta=(0., 0., 0.)):
    """Competition-normalized winning probabilities; no odds/results in input."""
    x = _features(race)
    b = race["heads"][HEADS[0]]
    return _softmax([math.log(max(p, EPS)) +
                     sum(t * z for t, z in zip(theta, v)) for p, v in zip(b, x)])


def _winner_index(race):
    return race["nos"].index(race["order"][0])


def fit(train, penalty, active=(0, 1, 2), steps=650):
    """Deterministic L2-regularized multinomial conditional-logit optimizer."""
    if not train:
        raise ValueError("empty training set")
    theta = [0., 0., 0.]
    data = [(r, _features(r), _winner_index(r)) for r in train]
    for step in range(steps):
        grad = [penalty * t for t in theta]
        for race, x, winner in data:
            probs = predict(race, theta)
            for k in active:
                grad[k] += (sum(p * row[k] for p, row in zip(probs, x))
                            - x[winner][k]) / len(data)
        rate = .12 / (1 + step / 250)
        for k in active:
            theta[k] = max(-3., min(3., theta[k] - rate * grad[k]))
    return tuple(theta)


def _extract(payloads):
    eligible_rows = []
    excluded = Counter()
    hashes = []
    ids = set()
    for label, payload in payloads:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
        hashes.append({"input": label, "sha256CanonicalJson": hashlib.sha256(raw).hexdigest()})
        for detail in payload.get("details") or []:
            if not isinstance(detail, dict):
                excluded["invalid-detail"] += 1
                continue
            key = (detail.get("date"), detail.get("id"))
            if key in ids:
                raise ValueError("duplicate race identity")
            ids.add(key)
            row, reason = eligible(detail)
            if row is None:
                excluded[reason] += 1
                continue
            if any(row["heads"][k] is None for k in HEADS):
                excluded["incomplete-original-heads"] += 1
                continue
            if set(row["order"][:3]) - set(row["nos"]):
                excluded["podium-not-in-runners"] += 1
                continue
            eligible_rows.append(row)
    return sorted(eligible_rows, key=lambda r: (r["date"], r["id"])), dict(excluded), hashes, len(ids)


def load_files(directory):
    for path in sorted(directory.glob("*.json")):
        yield path.name, json.loads(path.read_text(encoding="utf-8"))


def load_api(base, start, end):
    from datetime import date, timedelta
    current, last = date.fromisoformat(start), date.fromisoformat(end)
    if current > last:
        raise ValueError("end before start")
    while current <= last:
        day = current.isoformat()
        url = base.rstrip("/") + "/api/day?" + urllib.parse.urlencode(
            {"date": day, "details": "1"})
        request = urllib.request.Request(url, headers={
            "User-Agent": "ARVEXQ-Sealed-Conditional-Research/1.0",
            "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=75) as response:
            payload = json.load(response)
        if not isinstance(payload.get("details"), list):
            raise ValueError("API did not return full details for " + day)
        yield day, payload
        current += timedelta(days=1)


def experiment(payloads, train_end="2026-10-09",
               valid_end="2026-10-11", test_end="2026-10-13"):
    races, excluded, hashes, count = _extract(payloads)
    train = [r for r in races if r["date"] <= train_end]
    valid = [r for r in races if train_end < r["date"] <= valid_end]
    test = [r for r in races if valid_end < r["date"] <= test_end]
    result = {
        "version": VERSION, "status": "insufficient-data", "productionPromoted": False,
        "currentProductionEngineEvaluated": False,
        "baseline": "authentic historical locked decisionProbability (NOT current main)",
        "raceDetails": count, "eligibleWithAllHeads": len(races),
        "exclusions": excluded, "sourceHashes": hashes,
        "split": {label: {"count": len(items), "dates": sorted({x["date"] for x in items})}
                  for label, items in (("train", train), ("valid", valid), ("test", test))},
        "limitations": [
            "This is a study of historical frozen model heads, not current 45/35/20 inputs.",
            "Only a short archived period; 10/12-13 outcomes were already inspected in prior work.",
            "The holdout is chronological but NOT a fresh untouched independent future test.",
            "No pre-off market prices, pace scenarios, ROI, or independent A/B/C calibration.",
            "Plackett-Luce place/third marginals require separate empirical validation.",
        ],
    }
    if min(map(len, (train, valid, test))) < 15:
        return result

    baseline = lambda r: predict(r)
    candidates = []
    for active, label in (((0,), "P1"), ((0, 1), "P1+P2"),
                          ((0, 1, 2), "P1+P2+P3")):
        for penalty in (.05, .2, .8, 3.):
            theta = fit(train, penalty, active)
            pred = lambda r, weights=theta: predict(r, weights)
            candidates.append({"name": label, "l2": penalty, "theta": theta,
                               "validLoss": summarize(valid, pred)["logLoss"]})
    candidates.sort(key=lambda x: (x["validLoss"], sum(abs(y) for y in x["theta"])))
    best = candidates[0]
    theta = best["theta"]
    proposed = lambda r: predict(r, theta)
    baseline_valid = summarize(valid, baseline)
    proposed_valid = summarize(valid, proposed)
    baseline_test = summarize(test, baseline)
    proposed_test = summarize(test, proposed)
    paired = paired_bootstrap(test, baseline, proposed)
    by_circuit = {}
    for circuit in sorted({r["circuit"] for r in test}):
        subset = [r for r in test if r["circuit"] == circuit]
        by_circuit[circuit] = {"n": len(subset),
                               "baseline": summarize(subset, baseline),
                               "candidate": summarize(subset, proposed)}
    improvement = proposed_test["logLoss"] < baseline_test["logLoss"] and (
        proposed_test["brier"] < baseline_test["brier"])
    result.update({
        "status": "exploratory-evaluated", "chosenOnValidationOnly": best,
        "validation": {"baseline": baseline_valid, "candidate": proposed_valid},
        "holdout": {"baseline": baseline_test, "candidate": proposed_test,
                    "paired": paired, "byCircuit": by_circuit},
        "holdoutBothProperScoresBetter": improvement,
        "promotionDecision": "REJECT: no fresh current-engine pre-off holdout",
        "productionPromoted": False,
    })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--api-base", default="https://kraiz-api.4b89h4fydd.workers.dev")
    parser.add_argument("--start", default="2026-10-07")
    parser.add_argument("--end", default="2026-10-13")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payloads = load_files(args.result_dir) if args.result_dir else load_api(
        args.api_base, args.start, args.end)
    report = experiment(payloads)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                   allow_nan=False) + "\n", encoding="utf-8")
    brief = {k: report.get(k) for k in (
        "status", "raceDetails", "eligibleWithAllHeads", "split",
        "chosenOnValidationOnly", "holdoutBothProperScoresBetter",
        "promotionDecision")}
    if "holdout" in report:
        brief["holdout"] = {k: {q: v for q, v in metrics.items()
                                  if q in ("races", "logLoss", "brier", "top1Rate", "top3Rate")}
                            for k, metrics in report["holdout"].items()
                            if k in ("baseline", "candidate")}
        brief["paired"] = report["holdout"]["paired"]
    print("ARVEXQ_FROZEN_CHALLENGER_RESULT=" + json.dumps(
        brief, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
