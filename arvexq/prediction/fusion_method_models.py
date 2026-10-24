"""Train three independently auditable *methods* from dated racing history.

These are transparent public-method implementations, NOT the actual published
picks of みねた氏 or any other human forecaster. They never use the target race
result or odds. Learnt bucket win frequencies (not hand-set blending weights)
produce independent probability distributions for the existing fusion model.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from itertools import permutations
from math import isfinite
import json

from arvexq.prediction.mineta_public_pace import public_pace_factors
from arvexq.prediction.past_performance import analyze_past_performance
from arvexq.prediction.empirical_fusion import _timestamp

VERSION = "arvexq-fusion-observed-method-buckets-v1"
METHODS = ("mineta", "expert:form", "expert:course")
HISTORICAL_PRIOR = 0.5  # symmetric Jeffreys smoothing, NOT a ranking weight


def _active(detail):
    if not isinstance(detail, dict) or not isinstance(detail.get("horses"), list):
        raise ValueError("race card required")
    if detail.get("circuit") not in ("中央", "地方"):
        raise ValueError("separate JRA or NAR circuit required")
    if ("帯広" in str(detail.get("track") or "") or
            detail.get("surface") in ("障害", "ばんえい")):
        raise ValueError("retired Banei/jumps unavailable")
    horses = [h for h in detail["horses"] if isinstance(h, dict) and
              not (h.get("scratched") or h.get("withdrawn") or h.get("cancelled")) and
              str(h.get("status") or "") not in ("取消", "出走取消", "除外")]
    nums = [h.get("horseNumber") for h in horses]
    if len(nums) < 5 or len(set(nums)) != len(nums) or any(type(n) is not int or n < 1 for n in nums):
        raise ValueError("full active field required")
    return horses


def _binrate(value):
    if value is None:
        return "unknown"
    if type(value) not in (float, int) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("invalid observed rate")
    return "none" if value == 0 else "low" if value < .34 else "mid" if value < .67 else "high"


def _bucket(method, pace, entry, analysis):
    if method == "mineta":
        no = entry["horseNumber"]
        neighbors = {n for pair in pace["adjacentForwardCandidates"] for n in pair}
        return json.dumps({
            "lastEarly": entry["lastFirstCornerTop3"],
            "distance": entry["lastRunDistanceChange"],
            "neighborForward": no in neighbors,
            "firstCornerShortOfficial": pace["firstCornerShortPublicRule"],
            "forwardShare": _binrate(pace["forwardCandidateShare"]),
        }, sort_keys=True, ensure_ascii=False)
    if method == "expert:form":
        return json.dumps({
            "top3": _binrate(analysis["top3Rate"]),
            "recentForm": _binrate(analysis["recentFormQuality"]),
            "marginPresent": analysis["marginObservedRuns"] > 0,
            "opponentLevelPresent": analysis["opponentLevelObservedRuns"] > 0,
            "frontFadeTwice": analysis["frontFadeCount"] >= 2,
        }, sort_keys=True, ensure_ascii=False)
    if method == "expert:course":
        return json.dumps({
            "comparableQuality": _binrate(analysis["comparableQuality"]),
            "comparableStarts": "2+" if analysis["comparableRuns"] >= 2 else
                                "1" if analysis["comparableRuns"] else "0",
            "sameTrackStarts": "2+" if analysis["trackMatchedRuns"] >= 2 else
                               "1" if analysis["trackMatchedRuns"] else "0",
            "goingObserved": analysis["goingMatchedRuns"] > 0,
        }, sort_keys=True, ensure_ascii=False)
    raise ValueError("unknown registered method")


def observed_buckets(detail):
    horses = _active(detail)
    pace = public_pace_factors(detail)
    by_no = {e["horseNumber"]: e for e in pace["horses"]}
    out = {method: {} for method in METHODS}
    for horse in horses:
        no = horse["horseNumber"]
        analysis = analyze_past_performance(horse, detail)
        if not analysis["datedRuns"]:
            raise ValueError("at least one dated prior start required for each runner")
        for method in METHODS:
            out[method][no] = _bucket(method, pace, by_no[no], analysis)
    return out


def _labels(detail, field):
    result = detail.get("result")
    if not isinstance(result, dict) or result.get("status") != "確定":
        raise ValueError("confirmed historical results required")
    finishers = result.get("finishers")
    if not isinstance(finishers, list):
        raise ValueError("confirmed finish order required")
    labels = {}
    for row in finishers:
        if not isinstance(row, dict):
            continue
        no, finish = row.get("horseNumber"), row.get("finish")
        if type(no) is int and type(finish) is int and finish > 0:
            labels[no] = finish
    if len(labels) < len(field) or set(field) != set(labels) or sum(f == 1 for f in labels.values()) != 1:
        raise ValueError("complete unambiguous confirmed starter result required")
    return labels


def fit_observed_methods(details, *, circuit, target_date, min_races=30):
    """Frozen as-of-date method training, with all labels target-date earlier."""
    if circuit not in ("中央", "地方"):
        raise ValueError("separate circuit required")
    datetime.fromisoformat(target_date)
    observed, used_ids = {name: defaultdict(lambda: [0, 0]) for name in METHODS}, []
    seen = set()
    for race in sorted(details, key=lambda d: (d.get("date",""), d.get("id",""))):
        if not isinstance(race, dict) or race.get("circuit") != circuit:
            continue
        day, rid = race.get("date"), race.get("id")
        if not isinstance(day, str) or not day < target_date:
            continue
        if not rid or rid in seen:
            raise ValueError("duplicate historical training race")
        seen.add(rid)
        try:
            features = observed_buckets(race)
            labels = _labels(race, features["mineta"])
        except (TypeError, KeyError, ValueError):
            # Unverified historical rows do NOT train a method.
            continue
        for method, values in features.items():
            for no, bucket in values.items():
                record = observed[method][bucket]
                record[0] += 1  # sample count
                record[1] += int(labels[no] == 1)  # verified winner
        used_ids.append(rid)
    if len(used_ids) < min_races:
        raise ValueError("fewer than 30 earlier verified historical training races")
    models = {}
    for method in METHODS:
        counts = {k: list(v) for k, v in sorted(observed[method].items())}
        model = {"version": VERSION, "method": method, "circuit": circuit,
                 "trainingThrough": max(str(r["date"]) for r in details if r.get("id") in used_ids),
                 "trainingRaceIds": sorted(used_ids), "counts": counts,
                 "trainingCount": len(used_ids),
                 "formula": "grouped historical win-frequency with Jeffreys smoothing",
                 "notOriginalTipsterForecast": True}
        model["modelVersion"] = method + "/" + sha256(json.dumps(
            model, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        models[method] = model
    return models


def _order_probabilities(numbers, scores):
    """Exact PL top-three finish distribution: all probabilities match marginals."""
    normal = sum(scores.values())
    if not normal or any(not isfinite(x) or x <= 0 for x in scores.values()):
        raise ValueError("no finite empirical model scores")
    joint = []
    win = {no: 0.0 for no in numbers}
    podium = {no: 0.0 for no in numbers}
    for first, second, third in permutations(numbers, 3):
        a, b, c = scores[first], scores[second], scores[third]
        # Sum remaining weights directly: subtracting a near-certain winner
        # from normal loses small remaining mass to floating-point rounding.
        after_first = sum(scores[n] for n in numbers if n != first)
        after_second = sum(scores[n] for n in numbers if n not in (first,second))
        p = (a/normal) * (b/after_first) * (c/after_second)
        joint.append({"combo": [first, second, third], "probability": p})
        win[first] += p
        for no in (first, second, third):
            podium[no] += p
    return win, podium, joint


def predict_observed_methods(detail, models, *, captured_at, scheduled_off_at):
    """Return three independent recorded methodological candidates, no fake humans."""
    if _timestamp(captured_at) >= _timestamp(scheduled_off_at):
        raise ValueError("method candidate must be calculated before scheduled off")
    if (detail.get("result") or {}).get("finishers") or (detail.get("result") or {}).get("payouts"):
        raise ValueError("target outcome present in source; refuse race prediction")
    if not isinstance(models, dict) or set(models) != set(METHODS):
        raise ValueError("all three observed methodology models required")
    fields = observed_buckets(detail)
    roster = sorted(fields["mineta"])
    results = {}
    day = detail["date"]
    for method in METHODS:
        model = models[method]
        if (model.get("method") != method or model.get("circuit") != detail.get("circuit")
                or model.get("trainingThrough", "") >= day):
            raise ValueError("cross-circuit or future method training")
        scores = {}
        for no, bucket in fields[method].items():
            sample, wins = model["counts"].get(bucket, [0, 0])
            scores[no] = (wins + HISTORICAL_PRIOR) / (sample + 2*HISTORICAL_PRIOR)
        win, top3, triples = _order_probabilities(roster, scores)
        eid = sha256(json.dumps([detail["id"], method, fields[method],
                                 model["modelVersion"], captured_at],
                                ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        results[method] = {
            "raceId": detail["id"], "capturedAt": captured_at,
            "modelVersion": model["modelVersion"], "evidenceId": eid,
            "win": win, "top3": top3, "trifecta": triples,
            "sourceKind": "trained-public-method-implementation",
            "notOriginalTipsterForecast": True,
        }
    return results
