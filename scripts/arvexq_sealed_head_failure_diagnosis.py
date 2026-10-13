#!/usr/bin/env python3
"""Diagnose why sealed-head correction worsened. No production changes."""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from scripts.arvexq_sealed_conditional_challenger import (
    _extract, fit, load_api, predict,
)
from scripts.arvexq_integrated_research import summarize


def profile(races, old, new):
    groups = defaultdict(list)
    worst = []
    for race in races:
        winner = race["nos"].index(race["order"][0])
        p, q = old(race)[winner], new(race)[winner]
        delta = math.log(max(p, 1e-12)) - math.log(max(q, 1e-12))
        groups["all"].append(delta)
        groups["date:" + race["date"]].append(delta)
        groups["circuit:" + str(race["circuit"])].append(delta)
        groups["baseline-winner:" + ("under10" if p < .1 else "10to25" if p < .25 else "over25")].append(delta)
        worst.append({"race": race["id"], "winner": race["order"][0],
                      "before": p, "after": q, "lossIncrease": delta})
    return {
        "groups": {k: {"races": len(v), "meanLogLossIncrease": sum(v)/len(v),
                        "worse": sum(x > 1e-10 for x in v), "better": sum(x < -1e-10 for x in v)}
                   for k, v in sorted(groups.items())},
        "worstRaces": sorted(worst, key=lambda v: -v["lossIncrease"])[:15],
    }


def diagnose(payloads):
    races, excluded, hashes, total = _extract(payloads)
    train = [r for r in races if r["date"] <= "2026-10-09"]
    valid = [r for r in races if "2026-10-10" <= r["date"] <= "2026-10-11"]
    test = [r for r in races if "2026-10-12" <= r["date"] <= "2026-10-13"]
    report = {"version": "sealed-head-failure-diagnosis-v1", "totalRaces": total,
              "eligibleRaces": len(races), "excluded": excluded,
              "split": [len(train), len(valid), len(test)],
              "notFreshBlindTest": True, "productionChanged": False}
    if min(len(train), len(valid), len(test)) < 15:
        report["status"] = "insufficient-data"
        return report
    baseline = lambda r: predict(r)
    bvalid = summarize(valid, baseline)
    candidates = []
    for active, name in (((0,), "P1"), ((0,1), "P1+P2"), ((0,1,2), "P1+P2+P3")):
        for penalty in (.05, .2, .8, 3.):
            theta = fit(train, penalty, active)
            for shrink in (0., .1, .25, .5, 1.):
                weights = tuple(t * shrink for t in theta)
                fn = lambda r, w=weights: predict(r, w)
                m = summarize(valid, fn)
                candidates.append({"name": name, "penalty": penalty, "shrink": shrink,
                    "weights": weights, "logLoss": m["logLoss"], "brier": m["brier"],
                    "pass": m["logLoss"] <= bvalid["logLoss"]-.005
                            and m["brier"] <= bvalid["brier"]-.001})
    original = min((c for c in candidates if c["shrink"] == 1.),
                   key=lambda c: c["logLoss"])
    old = lambda r: predict(r, original["weights"])
    safe = [c for c in candidates if c["pass"]]
    selected = min(safe, key=lambda c: (c["logLoss"], c["brier"])) if safe else None
    guarded = (lambda r: predict(r, selected["weights"])) if selected else baseline
    report.update({"status": "diagnosed",
                   "baselineValidation": bvalid,
                   "originalCandidate": original,
                   "originalValidation": summarize(valid, old),
                   "originalHoldout": summarize(test, old),
                   "baselineHoldout": summarize(test, baseline),
                   "originalFailures": profile(test, baseline, old),
                   "guardedChoice": selected or "KEEP_BASELINE",
                   "guardedHoldout": summarize(test, guarded),
                   "guardedFailures": profile(test, baseline, guarded),
                   "selectionMethod": "training fit; validation selects/shrinks; holdout used for diagnosis only",
                   "promote": False})
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = diagnose(load_api("https://kraiz-api.4b89h4fydd.workers.dev",
                               "2026-10-07", "2026-10-13"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print("FAILURE_DIAGNOSIS=" + json.dumps({
        "status": result["status"], "split": result["split"],
        "originalCandidate": result.get("originalCandidate"),
        "originalFailures": result.get("originalFailures"),
        "guardedChoice": result.get("guardedChoice"),
        "guardedHoldout": result.get("guardedHoldout"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
