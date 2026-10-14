#!/usr/bin/env python3
"""Actual executed retrospective audit for PR112. Never call this pre-off validation."""
from __future__ import annotations
import base64
from collections import defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
from arvexq.prediction.factor_model import rank_factor_model
from scripts.arvexq_current_prediction_audit import finish_order, api_json


def fresh_box():
    return {"races": 0, "winnerTop1": 0, "winnerTop3": 0, "lossSum": 0., "brierSum": 0.}


def collect(box, predictions, winner):
    order = sorted(predictions, key=lambda n: (-predictions[n], n))
    mx = max(predictions.values())
    weights = {n: math.exp(5 * (s-mx)) for n, s in predictions.items()}
    total = sum(weights.values())
    probabilities = {n: w/total for n, w in weights.items()}
    box["races"] += 1
    box["winnerTop1"] += int(order[0] == winner)
    box["winnerTop3"] += int(winner in order[:3])
    box["lossSum"] += -math.log(max(probabilities[winner], 1e-15))
    box["brierSum"] += sum((p - int(n == winner)) ** 2 for n, p in probabilities.items())


def summary(box):
    n = box["races"]
    return {"races": n, "winRate": round(box["winnerTop1"]/n, 6) if n else None,
            "winnerTop3": round(box["winnerTop3"]/n, 6) if n else None,
            "logLoss": round(box["lossSum"]/n, 6) if n else None,
            "brier": round(box["brierSum"]/n, 6) if n else None}


def snapshot(path):
    data = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(data, dict) or "gzipBase64" not in data:
        return None
    raw = gzip.decompress(base64.b64decode(data["gzipBase64"]))
    if hashlib.sha256(raw).hexdigest() != data.get("sha256"):
        raise ValueError("snapshot digest mismatch: " + path.name)
    return json.loads(raw)


def locked_ranking(race):
    lock = race.get("preRacePrediction")
    if not isinstance(lock, dict):
        return []
    horses = lock.get("horses") or []
    scored = []
    for h in horses:
        if not isinstance(h, dict):
            continue
        no = int(h.get("horseNumber") or 0)
        ev = h.get("lockedEvaluation") or {}
        score = ev.get("coreAbilityScore", ev.get("score"))
        if no and isinstance(score, (int, float)) and math.isfinite(score):
            scored.append((no, float(score)))
    return scored


def alternative_scores(ranked, weight):
    """Independent older-than-five form; never reuse the recent five as ability."""
    out = {}
    for row in ranked:
        num = int(row["horse"].get("horseNumber") or 0)
        career = row.get("careerProfile") or {}
        prior = career.get("olderAbilityQuality")
        sample = int(career.get("olderAbilitySamples") or 0)
        shrink = weight * min(1., sample / 5.) if sample >= 3 and prior is not None else 0.
        if not shrink:
            out[num] = float(row["score"])
        else:
            out[num] = (1. - shrink) * float(row["score"]) + shrink * (
                0.5 + 0.65 * (float(prior) - 0.5))
    return out


def compact(box):
    return summary(box)


def main():
    target_dates = [(date(2026, 10, 7)+timedelta(days=i)).isoformat() for i in range(7)]
    outcomes = {}
    failed_dates = []
    for ds in target_dates:
        try:
            details = api_json("https://kraiz-api.4b89h4fydd.workers.dev/api/day?date="+ds+"&details=1").get("details") or []
            for d in details:
                if not isinstance(d, dict):
                    continue
                order = finish_order(d)
                if len(order) >= 3 and len(set(order[:3])) == 3:
                    outcomes[(str(d.get("date")), str(d.get("id")))] = order
        except Exception as exc:
            failed_dates.append({"date": ds, "error": type(exc).__name__})
    counts = defaultdict(int)
    metrics = defaultdict(fresh_box)
    for path in sorted(Path("arvexq/ui/static/saved-snapshots").glob("*.json")):
        race = snapshot(path)
        if not isinstance(race, dict):
            continue
        counts["hashValidSnapshots"] += 1
        circuit = str(race.get("circuit") or "unknown")
        outcome = outcomes.get((str(race.get("date")), str(race.get("id"))))
        if not outcome:
            counts["missingOfficialResult"] += 1
            continue
        ranked = rank_factor_model(race.get("horses") or [], race)
        vals = {int(x["horse"].get("horseNumber") or 0): float(x["score"]) for x in ranked}
        if outcome[0] not in vals or len(vals) < 3:
            counts["missingCandidateInputs"] += 1
            continue
        counts["candidateRetrospectiveRaces"] += 1
        collect(metrics[(circuit, "candidateRetrospective")], vals, outcome[0])
        # Candidate exploration must be scored against the same winner/roster,
        # with the last three dates held out from exploratory calibration.
        phase = "holdout" if str(race.get("date") or "") >= "2026-10-11" else "explore"
        collect(metrics[(circuit, phase, "baseline")], vals, outcome[0])
        counts[circuit+"|"+phase+"|olderAvailable"] += sum(1 for row in ranked if (row.get("careerProfile") or {}).get("olderAbilitySamples",0)>=3)
        counts[circuit+"|"+phase+"|runners"] += len(ranked)
        for weight in (0.1, 0.2, 0.3, 0.4, 0.5, 0.65):
            alt = alternative_scores(ranked, weight)
            collect(metrics[(circuit, phase, f"olderAbility_{weight}")], alt, outcome[0])
        original = locked_ranking(race)
        original_vals = dict(original)
        if len(original_vals) == len(vals) and set(original_vals) == set(vals):
            collect(metrics[(circuit, "originalLockedScore")], original_vals, outcome[0])
            counts["pairedWithOriginalScores"] += 1
        else:
            counts["originalScoresUnavailableOrDifferentRoster"] += 1
    output = {"version": "arvexq-pr112-retrospective-execution-v1",
              "dates": target_dates, "officialResults": len(outcomes),
              "failedDates": failed_dates, "counts": dict(counts),
              "byCircuitAndMethod": {"|".join(key): summary(box)
                  for key, box in sorted(metrics.items())},
              "experimentPolicy": "Explore 2026-10-07 through 10, holdout 11 through 13; candidate is not a production approval.",
              "featureCoverageShift": {
                  circuit: {
                      phase: {
                          "available": counts[circuit+"|"+phase+"|olderAvailable"],
                          "runners": counts[circuit+"|"+phase+"|runners"],
                          "fraction": round(counts[circuit+"|"+phase+"|olderAvailable"] /
                              max(1, counts[circuit+"|"+phase+"|runners"]), 6)}
                      for phase in ("explore", "holdout")}
                  for circuit in ("中央", "地方")},
              "candidateDeploymentEligible": False,
              "candidateDeploymentBlockers": [
                  "unverified_preoff_features",
                  "explore_to_holdout_older_career_coverage_shift",
                  "no_head_to_head_sealed_baseline"],
              "authenticatedPreoffFeatureRaces": 0,
              "note": "NON-PREOFF retrospective replay; candidate uses stored mutable feature histories. Fixed temperature 5 for relative log loss/Brier only. Do not merge based on this."}
    print("PR112_RETROSPECTIVE_AUDIT=" + json.dumps(output, ensure_ascii=False))
    if failed_dates:
        raise SystemExit("official outcome API incomplete")
    if not counts["candidateRetrospectiveRaces"]:
        raise SystemExit("no matchable finalized outcomes")


if __name__ == "__main__":
    main()
