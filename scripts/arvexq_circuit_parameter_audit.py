#!/usr/bin/env python3
"""Leakage-labelled, time-split exploration of independent JRA/NAR policies.

This script deliberately never rewrites predictions, tickets, archives or weights.
Stored outer snapshots have NOT been authenticated as captured pre-off:
results are diagnostic retrospective replay, not proof of deployable accuracy.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import product
import json
import math
from pathlib import Path

from arvexq.prediction.circuit_models import circuit_key
from arvexq.prediction.factor_model import collect_horse_raw_metrics
from arvexq.prediction.past_performance import observed_runs
from arvexq.core.runner_status import is_inactive_runner
from scripts.arvexq_current_prediction_audit import api_json, finish_order
from scripts.arvexq_pr112_retrospective_execution import snapshot

DATES = [(date(2026, 10, 7) + timedelta(days=i)).isoformat() for i in range(7)]
CIRCUITS = ("JRA", "NAR")


def _quality(run):
    field, finish = run.get("fieldSize"), run.get("finish")
    if not isinstance(field, (float, int)) or not isinstance(finish, (float, int)):
        return None
    if field < 2 or not 1 <= finish <= field:
        return None
    return (field-finish)/(field-1)


def features(horse, race):
    raw = collect_horse_raw_metrics(horse, race)
    runs = observed_runs(horse, race, limit=5)
    q = [_quality(x) for x in runs]
    q = [x for x in q if x is not None]
    trend = ((q[0]+q[1])-(q[-1]+q[-2]))/2 if len(q) >= 4 else None
    track = str(race.get("track") or "").strip()
    same = [_quality(x) for x in runs if track and str(x.get("track") or "").strip() == track]
    same = [x for x in same if x is not None]
    return (raw, trend, sum(same)/len(same) if len(same)>=2 else None)


def score(x, params, circuit):
    raw, trend, track = x
    recent = raw["recentForm"]
    if recent is None:
        return .5
    score = float(recent)
    condition = raw.get("conditionForm")
    if condition is not None:
        per, cap = params["condition"], params["cap"]
        w = min(cap, per * int(raw.get("conditionRuns") or 0))
        score = (1-w)*score + w*condition
    if circuit == "JRA" and trend is not None:
        score += params["momentum"] * max(-.30, min(.30, trend))
    if circuit == "NAR" and track is not None:
        w = params["track"]
        score = (1-w)*score + w*track
    return min(1., max(0., score))


def evaluate(rows, params, circuit, temp):
    wins = top3 = 0
    ll = brier = 0.
    for xs, winner in rows:
        values = {n: score(x, params, circuit) for n, x in xs.items()}
        if winner not in values:
            raise ValueError("missing winner in evaluated runner set")
        order = sorted(values, key=lambda n: (-values[n], n))
        wins += winner == order[0]
        top3 += winner in order[:3]
        largest = max(values.values())
        exp = {n: math.exp(temp*(v-largest)) for n, v in values.items()}
        z = sum(exp.values())
        prob = {n: v/z for n,v in exp.items()}
        ll += -math.log(max(prob[winner],1e-15))
        brier += sum((v-(n==winner))**2 for n,v in prob.items())
    n=len(rows)
    if not n:
        return None
    return {"races": n, "top1": round(wins/n, 6), "winnerTop3": round(top3/n, 6),
            "logLoss": round(ll/n, 6), "brier": round(brier/n, 6)}


def grid(circuit):
    # No legacy sectional, odds or post-result data enters any model score.
    if circuit == "JRA":
        return [{"condition":c, "cap":min(.25, c*3), "momentum":m, "track":0.}
                for c,m in product((0.,.02,.04,.06,.08), (-.08,-.04,0.,.04,.08,.12))]
    return [{"condition":c, "cap":min(.30,c*3), "momentum":0., "track":t}
            for c,t in product((0.,.04,.08,.12), (0.,.05,.10,.20,.30))]


def _baseline_params(circuit):
    return ({"condition":.04,"cap":.12,"momentum":.06,"track":0.}
            if circuit=="JRA" else
            {"condition":.08,"cap":.25,"momentum":0.,"track":.10})


def main():
    results={}
    failures=[]
    for day in DATES:
        try:
            data=api_json("https://kraiz-api.4b89h4fydd.workers.dev/api/day?date="+day+"&details=1")
            for item in data.get("details") or []:
                order=finish_order(item)
                if len(order)>=3 and len(set(order[:3]))==3:
                    results[(str(item.get("date")),str(item.get("id")))]=order[0]
        except Exception as exc:
            failures.append({"day":day,"error":type(exc).__name__})
    if failures:
        raise RuntimeError("incomplete official result coverage: "+str(failures))

    grouped={c: {"train":[],"holdout":[]} for c in CIRCUITS}
    counts=Counter()
    for path in sorted(Path("arvexq/ui/static/saved-snapshots").glob("*.json")):
        race=snapshot(path)
        if not isinstance(race,dict):
            continue
        c=circuit_key(race)
        if c not in CIRCUITS:
            continue
        winner=results.get((str(race.get("date")),str(race.get("id"))))
        if winner is None:
            counts[c+"|unmatched"]+=1
            continue
        xs={}
        for horse in race.get("horses") or []:
            if not isinstance(horse,dict) or is_inactive_runner(horse):
                continue
            no=int(horse.get("horseNumber") or 0)
            if no>0:
                xs[no]=features(horse,race)
        if winner not in xs or len(xs)<3 or not any(v[0].get("recentForm") is not None for v in xs.values()):
            counts[c+"|incomplete"]+=1
            continue
        phase="train" if str(race.get("date") or "")<="2026-10-10" else "holdout"
        grouped[c][phase].append((xs,winner))
        counts[c+"|"+phase]+=1
        counts[c+"|"+phase+"|missingFiveRuns"]+=sum(int(x[0].get("sample") or 0)<5 for x in xs.values())

    out={"version":"arvexq-circuit-search-research-v1",
         "dataIntegrity":"RETROSPECTIVE_ONLY_NOT_AUTHENTICATED_PREOFF",
         "split":{"train":DATES[:4],"holdout":DATES[4:]},
         "counts":dict(counts),"circuits":{}}
    for c in CIRCUITS:
        train,holdout=grouped[c]["train"],grouped[c]["holdout"]
        if len(train)<10 or len(holdout)<10:
            raise RuntimeError(f"not enough disjoint {c} races")
        bas=_baseline_params(c)
        baseline_train=evaluate(train,bas,c,5.)
        baseline_holdout=evaluate(holdout,bas,c,5.)
        # Training winner log loss selects the policy. Holdout is viewed once.
        candidates=[]
        for p,temp in product(grid(c),(3.,4.,5.,6.,7.,8.,10.)):
            m=evaluate(train,p,c,temp)
            candidates.append((m["logLoss"],m["brier"],p,temp,m))
        candidates.sort(key=lambda x:(x[0],x[1],str(x[2]),x[3]))
        best=candidates[0]
        challenger=evaluate(holdout,best[2],c,best[3])
        # Extra guardrails prevent publication based on chance / post-off data.
        out["circuits"][c]={
            "trainBaseline":baseline_train,"holdoutBaseline":baseline_holdout,
            "selectedOnTrain":{"parameters":best[2],"temperature":best[3],"metrics":best[4]},
            "holdoutChallenger":challenger,
            "holdoutImprovement":{
                "logLoss":round(baseline_holdout["logLoss"]-challenger["logLoss"],6),
                "brier":round(baseline_holdout["brier"]-challenger["brier"],6),
                "top1":round(challenger["top1"]-baseline_holdout["top1"],6),
                "top3":round(challenger["winnerTop3"]-baseline_holdout["winnerTop3"],6)},
            "releaseEligible":False,
            "releaseBlockers":["preoff_feature_capture_unverified",
                "historical_coverage_shift","prospective_calibration_missing"],
        }
    print("ARVEXQ_CIRCUIT_PARAMETER_AUDIT="+json.dumps(out,ensure_ascii=False))
    # Successful exploration is a diagnostic completion, never model approval.


if __name__=="__main__":
    main()
