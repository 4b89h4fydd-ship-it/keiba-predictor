#!/usr/bin/env python3
"""Offline audit and date-separated calibration experiment; NEVER writes forecasts.

Input: immutable static envelopes and downloaded Actions day-API artifacts.
Only frozen pre-off lock rows are prediction evidence. Day results are labels.
No final odds, reconstructed horse features, or post-race scores are predictors.
"""
from __future__ import annotations
import argparse
import base64
import collections
import gzip
import hashlib
import json
import math
import random
import statistics
import time
from pathlib import Path

from arvexq.components.item_147.prerace_archive import post_at, sealed_lock

VERSION = "arvexq-integrated-research-v1"


def finite(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def probability_vector(rows, key):
    values = [finite(h.get(key)) for h in rows]
    if not values or any(x is None or not 0 <= x <= 1 for x in values):
        return None
    total = sum(values)
    if abs(total - 1) > 1e-5:
        return None
    # Remove only storage rounding error, never repair an invalid distribution.
    return [x / total for x in values]


def eligible(detail):
    lock = sealed_lock(detail)
    if lock is None:
        return None, "missing-authentic-frozen-lock"
    post = post_at(detail)
    if lock.get("sealedAtEpoch") is not None:
        stamp = finite(lock["sealedAtEpoch"])
        # Existing sealer supplies a clock sampled before browser capture.
        # Reversed clocks are a separate diagnostic, not proof of post-off input.
        if stamp is None or not 0 < stamp < post.timestamp():
            return None, "seal-time-invalid"
    result = detail.get("result") or {}
    if result.get("status") != "確定":
        return None, "result-not-final"
    pairs = []
    for row in result.get("finishers") or []:
        try:
            pos, no = int(row["finish"]), int(row["horseNumber"])
        except (KeyError, TypeError, ValueError):
            continue
        if pos > 0 and no > 0:
            pairs.append((pos, no))
    pairs.sort()
    if (len(pairs) < 3 or [p for p, _ in pairs[:3]] != [1, 2, 3]
            or len({p for p, _ in pairs}) != len(pairs)
            or len({n for _, n in pairs}) != len(pairs)):
        return None, "missing-unique-podium-or-dead-heat"
    rows = lock["horses"]
    nos = [int(h["horseNumber"]) for h in rows]
    order = [no for _, no in pairs]
    if not set(order[:3]).issubset(nos):
        return None, "podium-not-in-original-runner-set"
    heads = {k: probability_vector(rows, k) for k in
             ("decisionProbability", "p1Probability", "p2Probability", "p3Probability")}
    return {"id": detail["id"], "date": detail["date"],
            "circuit": detail.get("circuit", "unknown"), "track": detail.get("track"),
            "modelVersion": lock.get("modelVersion"), "surface": detail.get("surface"),
            "distance": detail.get("distance"), "nos": nos, "order": order,
            "heads": heads, "lock": lock}, "eligible"


def wilson(hits, total):
    if not total:
        return None
    z = 1.959963984540054
    p = hits / total
    den = 1 + z*z/total
    mid = (p + z*z/(2*total)) / den
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / den
    return [mid-half, mid+half]


def power(values, beta):
    logs = [beta * math.log(max(x, 1e-15)) for x in values]
    peak = max(logs)
    w = [math.exp(x-peak) for x in logs]
    return [x/sum(w) for x in w]


def race_metrics(race, probabilities):
    winner = race["nos"].index(race["order"][0])
    ranked = sorted(range(len(probabilities)), key=lambda i: (-probabilities[i], race["nos"][i]))
    return {"loss": -math.log(max(probabilities[winner], 1e-15)),
            "brier": sum((p-int(i == winner))**2 for i, p in enumerate(probabilities)),
            "top1": int(ranked[0] == winner), "top2": int(winner in ranked[:2]),
            "top3": int(winner in ranked[:3]),
            "podiumRecall": len({race["nos"][i] for i in ranked[:3]} & set(race["order"][:3]))/3,
            "confidence": probabilities[ranked[0]]}


def summarize(races, predictor):
    rows = [race_metrics(r, predictor(r)) for r in races]
    n = len(rows)
    if not n:
        return {"races": 0, "logLoss": None, "brier": None, "top1Rate": None}
    bins = []
    for lo in (0, .1, .2, .3, .4, .5, .6, .7, .8, .9):
        items = [x for x in rows if lo <= x["confidence"] < lo+.1+1e-12
                 and (lo == .9 or x["confidence"] < lo+.1)]
        if items:
            hits = sum(x["top1"] for x in items)
            bins.append({"lower": lo, "count": len(items),
                         "meanPredicted": statistics.mean(x["confidence"] for x in items),
                         "observed": hits/len(items), "wilson95": wilson(hits, len(items))})
    out = {"races": n, "logLoss": statistics.mean(x["loss"] for x in rows),
           "brier": statistics.mean(x["brier"] for x in rows),
           "top3SelectionPodiumRecall": statistics.mean(x["podiumRecall"] for x in rows),
           "leaderCalibration": bins}
    for key in ("top1", "top2", "top3"):
        hits = sum(x[key] for x in rows)
        out[key+"Hits"] = hits
        out[key+"Rate"] = hits/n
        out[key+"Wilson95"] = wilson(hits, n)
    return out


def paired_bootstrap(races, baseline, candidate):
    if not races:
        return None
    diffs = [race_metrics(r, candidate(r))["loss"]-race_metrics(r, baseline(r))["loss"] for r in races]
    rng = random.Random(20261013)
    draws = sorted(statistics.mean(rng.choices(diffs, k=len(diffs))) for _ in range(2000))
    return {"candidateMinusBaselineLogLoss": statistics.mean(diffs),
            "raceBootstrap95": [draws[49], draws[1949]], "resamples": 2000,
            "limitation": "race-level bootstrap; same-day dependence and model drift not resolved"}


def audit_snapshots(directory):
    counts = collections.Counter()
    days = collections.Counter()
    versions = collections.Counter()
    feature_counts = collections.Counter()
    seen = set()
    rows = []
    for path in sorted(directory.glob("*.json")):
        envelope = json.loads(path.read_text())
        if "gzipBase64" not in envelope:
            continue
        counts["envelopes"] += 1
        raw = gzip.decompress(base64.b64decode(envelope["gzipBase64"], validate=True))
        digest = hashlib.sha256(raw).hexdigest()
        if (digest != envelope.get("sha256") or path.stem != digest
                or len(raw) != envelope.get("bytes")):
            raise ValueError(f"immutable envelope integrity failed: {path.name}")
        d = json.loads(raw)
        identity = (d.get("id"), d.get("date"))
        if identity in seen:
            counts["duplicateRaceVersions"] += 1
        seen.add(identity)
        days[d.get("date")] += 1
        counts["sha256Verified"] += 1
        for key in ("preRacePrediction", "preRaceBet", "result", "massFeatureSnapshot"):
            counts[key] += bool(d.get(key))
        counts["sealed"] += sealed_lock(d) is not None
        lock = d.get("preRacePrediction") or {}
        versions[str(lock.get("modelVersion"))] += 1
        mass = d.get("massFeatureSnapshot") or {}
        counts["featureSnapshotWithCaptureTime"] += bool(mass.get("capturedAtEpoch"))
        from arvexq.prediction.factor_model import collect_horse_raw_metrics
        for h in d.get("horses") or []:
            feature_counts["horses"] += 1
            factors = collect_horse_raw_metrics(h, d)
            for key in ("trueRun", "pure", "sectional"):
                feature_counts[key+"Missing"] += factors[key] is None
        rows.append({"file": path.name, "sha256": digest, "raceId": d.get("id"),
                     "date": d.get("date"), "bytes": len(raw)})
    return {"counts": dict(counts), "byDate": dict(days), "archivedModelVersions": dict(versions),
            "currentRawFactorCoverage": dict(feature_counts), "manifest": rows}


def evaluate(result_dir):
    races, excluded = [], collections.Counter()
    all_dates, versions, nos_seen = collections.Counter(), collections.Counter(), set()
    input_hashes = []
    for path in sorted(result_dir.glob("*.json")):
        raw = path.read_bytes()
        input_hashes.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
        payload = json.loads(raw)
        for detail in payload.get("details") or []:
            key = (detail.get("id"), detail.get("date"))
            if key in nos_seen:
                raise ValueError("duplicate result race input")
            nos_seen.add(key)
            all_dates[detail.get("date")] += 1
            row, reason = eligible(detail)
            if row is None:
                excluded[reason] += 1
                continue
            versions[str(row["modelVersion"])] += 1
            races.append(row)
    common = [r for r in races if r["heads"]["decisionProbability"] is not None
              and r["heads"]["p1Probability"] is not None]
    baseline = lambda r: r["heads"]["decisionProbability"]
    p1 = lambda r: r["heads"]["p1Probability"]
    uniform = lambda r: [1/len(r["nos"])]*len(r["nos"])
    train = [r for r in common if r["date"] <= "2026-10-09"]
    valid = [r for r in common if "2026-10-10" <= r["date"] <= "2026-10-11"]
    test = [r for r in common if "2026-10-12" <= r["date"] <= "2026-10-13"]
    experiment = {"status": "insufficient-independent-periods", "promote": False,
                  "split": {k: {"races": len(v), "dates": sorted({r['date'] for r in v})}
                            for k, v in (("train", train), ("valid", valid), ("test", test))}}
    if train and valid and test:
        candidates = []
        for head in ("decisionProbability", "p1Probability"):
            grid = []
            for beta in (.25, .5, .75, 1, 1.25, 1.5, 2):
                pred = lambda r, h=head, b=beta: power(r["heads"][h], b)
                grid.append((summarize(train, pred)["logLoss"], beta))
            _, beta = min(grid)
            pred = lambda r, h=head, b=beta: power(r["heads"][h], b)
            candidates.append((summarize(valid, pred)["logLoss"], head, beta))
        # Only train/validation labels determine the candidate. Test is never tuned.
        _, head, beta = min(candidates)
        candidate = lambda r: power(r["heads"][head], beta)
        experiment.update({"status": "completed-research-only", "head": head, "beta": beta,
                           "valid": {"baseline": summarize(valid, baseline), "candidate": summarize(valid, candidate)},
                           "test": {"baseline": summarize(test, baseline), "candidate": summarize(test, candidate),
                                    "uniform": summarize(test, uniform)},
                           "paired": paired_bootstrap(test, baseline, candidate),
                           "promotionReason": "archived engine differs from current main; seven days cannot establish all-course generalization"})
    groups = {}
    for circuit in sorted({r["circuit"] for r in common}):
        subset = [r for r in common if r["circuit"] == circuit]
        groups[circuit] = {"baseline": summarize(subset, baseline), "savedP1": summarize(subset, p1)}
    rank_issues = collections.Counter()
    podium_brier, podium_log_loss = [], []
    mark_results = collections.defaultdict(lambda: {"runners": 0, "winHits": 0, "top3Hits": 0})
    failure_rows = []
    for r in races:
        lock = r["lock"]
        rank_issues["sealClockBeforeCapture"] += bool(
            finite(lock.get("sealedAtEpoch")) is not None
            and float(lock["sealedAtEpoch"]) < float(lock["capturedAtEpoch"]))
        for key, vals in r["heads"].items():
            rank_issues[key+"Invalid"] += vals is None
        vals = [r["heads"][key] for key in ("p1Probability", "p2Probability", "p3Probability")]
        if all(v is not None for v in vals):
            sums = [sum(v[i] for v in vals) for i in range(len(r["nos"]))]
            invalid = any(p > 1+1e-5 for p in sums)
            rank_issues["top3MarginalAboveOne"] += invalid
            if not invalid:
                target = set(r["order"][:3])
                for no, p in zip(r["nos"], sums):
                    y = int(no in target)
                    p = min(1., max(0., p))
                    podium_brier.append((p-y)**2)
                    podium_log_loss.append(-math.log(max(p if y else 1-p, 1e-15)))
        for row in r["lock"]["horses"]:
            no = int(row["horseNumber"])
            mark = str(row.get("mark") or "unmarked")
            stat = mark_results[mark]
            stat["runners"] += 1
            stat["winHits"] += no == r["order"][0]
            stat["top3Hits"] += no in r["order"][:3]
        if r in common:
            m = race_metrics(r, baseline(r))
            if not m["top1"]:
                failure_rows.append({"raceId": r["id"], "date": r["date"],
                                     "predicted": r["nos"][max(range(len(r["nos"])), key=lambda i: baseline(r)[i])],
                                     "winner": r["order"][0], "winnerLogLoss": m["loss"],
                                     "causalClassification": "not-identifiable-from-locked-probabilities-alone"})
    for stat in mark_results.values():
        stat["winRate"] = stat["winHits"]/stat["runners"]
        stat["top3Rate"] = stat["top3Hits"]/stat["runners"]
        stat["winWilson95"] = wilson(stat["winHits"], stat["runners"])
        stat["top3Wilson95"] = wilson(stat["top3Hits"], stat["runners"])
    return {"sourceFiles": input_hashes, "scheduledByDate": dict(all_dates), "scheduledRaces": len(nos_seen),
            "eligibleFrozenRaces": len(races), "pairedProbabilityRaces": len(common),
            "exclusions": dict(excluded), "archivedModelVersions": dict(versions),
            "probabilityValidity": dict(rank_issues),
            "allArchived": {"baseline": summarize(common, baseline), "savedP1": summarize(common, p1),
                            "uniform": summarize(common, uniform)}, "byCircuit": groups,
            "coherentArchivedPodiumMetrics": {"runnerRows": len(podium_brier),
                "brierPerRunner": statistics.mean(podium_brier) if podium_brier else None,
                "binaryLogLossPerRunner": statistics.mean(podium_log_loss) if podium_log_loss else None,
                "scope": "saved P1+P2+P3 only where every runner sum <=1; not decisionProbability+P2+P3"},
            "archivedMarks": dict(mark_results), "failedLeaderRaces": failure_rows,
            "calibrationExperiment": experiment,
            "currentMainAccuracy": None, "marketComparison": None, "ticketReturn": None,
            "limitations": ["No verified prediction-time market odds in locked rows",
                            "Archive reports are selected available days, not all-course proof",
                            "Saved P1/decision probabilities are different archived heads",
                            "No current-main independent performance claim", "No reconstructed or final features used"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot-dir", type=Path, default=Path("arvexq/ui/static/saved-snapshots"))
    p.add_argument("--result-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    start = time.monotonic()
    result = {"version": VERSION, "staticSnapshots": audit_snapshots(a.snapshot_dir),
              "evaluation": evaluate(a.result_dir), "originalsModified": 0, "productionModelChanged": False}
    result["elapsedSeconds"] = time.monotonic()-start
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    e = result["evaluation"]
    print(json.dumps({"scheduled": e["scheduledRaces"], "eligible": e["eligibleFrozenRaces"],
                      "paired": e["pairedProbabilityRaces"], "experiment": e["calibrationExperiment"]["status"]}))


if __name__ == "__main__":
    main()
