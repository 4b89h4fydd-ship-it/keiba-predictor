"""Research-only conditional second/third models for ARVEXQ goal B.

Stage 1 remains the existing win model. Stages 2 and 3 are fitted solely on
verified TRAINING labels, conditioning on the preceding finishers having been
removed. Inference marginalizes over EVERY possible earlier finish; it does
not peek at actual first/second-place outcomes.

No odds, marks, bets, production import or invented race evidence.
"""
from __future__ import annotations

from math import exp, isclose, isfinite, log
from hashlib import sha256
import json

from .race_softmax_research import _validate_race, _vector, _softmax, predict
from .top_three_joint_research import joint_top_three
from .frozen_pace_context import NAMES as PACE_NAMES, VERSION as PACE_VERSION, build_preoff_pace_context

VERSION = "arvexq-conditional-positions-research-v2-pace-context"


def _hash(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _vectors(race, win_model):
    context = build_preoff_pace_context(race)
    return [_vector(h, win_model) +
            [float(key not in h["features"]) for key in win_model["features"]] +
            context[i]
            for i, h in enumerate(race["horses"])]


def _stage_fit(races, win_model, stage, *, epochs, learning_rate, ridge):
    """Train categorical conditional likelihood for next finisher (stage 2/3)."""
    width = len(win_model["weights"]) + len(PACE_NAMES)
    weights = [0.] * width
    for _ in range(epochs):
        gradient = [ridge * w for w in weights]
        for race in races:
            xs = _vectors(race, win_model)
            remaining = [idx for idx, horse in enumerate(race["horses"])
                         if horse["finish"] >= stage]
            winner = next(idx for idx in remaining
                          if race["horses"][idx]["finish"] == stage)
            probs = _softmax([sum(w * v for w, v in zip(weights, xs[idx]))
                              for idx in remaining])
            for index, prob in zip(remaining, probs):
                error = prob - float(index == winner)
                for k, value in enumerate(xs[index]):
                    gradient[k] += error * value / len(races)
        weights = [max(-20., min(20., w - learning_rate * d))
                   for w, d in zip(weights, gradient)]
    return weights


def train_positions(train_races, win_model, *, epochs=150, learning_rate=.05,
                    ridge=.03):
    """Use only past training dates; never tune with validation/test finishes."""
    if not train_races or type(epochs) is not int or not 1 <= epochs <= 2000:
        raise ValueError("nonempty training races and valid epochs required")
    if not (0 < learning_rate <= .5 and 0 <= ridge <= 1):
        raise ValueError("invalid optimizer settings")
    if win_model.get("modelHash") != _hash(
            {k:v for k,v in win_model.items() if k != "modelHash"}):
        raise ValueError("win model integrity mismatch")
    if win_model.get("status") != "research-not-calibrated-not-production":
        raise ValueError("research-only win model required")
    if not win_model.get("features") or len(win_model["weights"]) != 2*len(win_model["features"]):
        raise ValueError("invalid frozen win feature dimensions")
    seen = set()
    for race in train_races:
        _validate_race(race, labelled=True)
        finishes = [h["finish"] for h in race["horses"]]
        if sorted(finishes) != list(range(1,len(finishes)+1)):
            raise ValueError("strict ordered training results required")
        if race["raceId"] in seen:
            raise ValueError("duplicate training race")
        seen.add(race["raceId"])
        if race["circuit"] != win_model["circuit"] or race["family"] != win_model["family"]:
            raise ValueError("cross-circuit training forbidden")
        if race["date"] > win_model["trainedThrough"] or race["raceId"] not in win_model["trainedRaceIds"]:
            raise ValueError("conditional training must use original win training partition")
    second = _stage_fit(train_races, win_model, 2, epochs=epochs,
                        learning_rate=learning_rate, ridge=ridge)
    third = _stage_fit(train_races, win_model, 3, epochs=epochs,
                       learning_rate=learning_rate, ridge=ridge)
    model = {"version":VERSION, "status":"research-only-uncalibrated",
             "winModelHash":win_model["modelHash"],"trainedThrough":win_model["trainedThrough"],
             "trainedRaceIds":sorted(seen),"circuit":win_model["circuit"],
             "family":win_model["family"],"features":list(win_model["features"]),
             "paceContextVersion":PACE_VERSION,"paceFeatureNames":list(PACE_NAMES),
             "secondWeights":second,"thirdWeights":third,
             "trainRaceCount":len(train_races),"trainingInputHash":_hash(train_races),
             "optimizer":{"epochs":epochs,"learningRate":learning_rate,"ridge":ridge},
             "promotionEligible":False}
    model["modelHash"] = _hash(model)
    return model


def predict_positions(position_model, win_model, race):
    """Marginalize over all first/second finishers; preserve podium normalization."""
    if position_model.get("modelHash") != _hash(
            {k:v for k,v in position_model.items() if k != "modelHash"}):
        raise ValueError("position model integrity mismatch")
    if position_model.get("version") != VERSION or position_model.get("winModelHash") != win_model.get("modelHash"):
        raise ValueError("model mismatch")
    if (position_model.get("features") != win_model.get("features")
            or position_model.get("paceContextVersion") != PACE_VERSION
            or position_model.get("paceFeatureNames") != list(PACE_NAMES)):
        raise ValueError("feature mismatch")
    if (position_model.get("circuit") != win_model.get("circuit")
            or position_model.get("family") != win_model.get("family")):
        raise ValueError("circuit/family mismatch")
    if (race.get("date","") <= position_model["trainedThrough"]
            or race.get("raceId") in position_model["trainedRaceIds"]):
        raise ValueError("lookahead prediction forbidden")
    win = predict(win_model, race)
    numbers = [row["horseNumber"] for row in win["rows"]]
    first = [row["winProbability"] for row in win["rows"]]
    xs = _vectors(race, win_model)
    n = len(xs)
    if n > 24:
        raise ValueError("field too large")
    def scores(name):
        w = position_model[name]
        if not isinstance(w,list) or len(w) != len(xs[0]) or any(type(v) not in (int,float) or not isfinite(v) for v in w):
            raise ValueError("invalid stage parameters")
        return [sum(a*b for a,b in zip(w,x)) for x in xs]
    score2, score3 = scores("secondWeights"), scores("thirdWeights")
    # Compute stable conditional softmax for each remaining runner set.
    podium = []
    marginal = {no:[0.,0.,0.] for no in numbers}
    for i in range(n):
        inds2 = [j for j in range(n) if j != i]
        probs2 = _softmax([score2[j] for j in inds2])
        for j,p2 in zip(inds2,probs2):
            inds3 = [k for k in range(n) if k not in (i,j)]
            probs3 = _softmax([score3[k] for k in inds3])
            for k,p3 in zip(inds3,probs3):
                p = first[i]*p2*p3
                podium.append({"first":numbers[i],"second":numbers[j],
                               "third":numbers[k],"probability":p})
                marginal[numbers[i]][0] += p
                marginal[numbers[j]][1] += p
                marginal[numbers[k]][2] += p
    total = sum(row["probability"] for row in podium)
    if not isclose(total,1.,abs_tol=1e-9):
        raise ValueError("non-normalized podium")
    if any(not isclose(sum(v[stage] for v in marginal.values()),1.,abs_tol=1e-9)
           for stage in range(3)):
        raise ValueError("non-normalized position marginals")
    return {"version":VERSION,"raceId":race["raceId"],
            "status":"research-only-position-uncalibrated",
            "method":"train-only-conditional-second-and-third-with-frozen-pace-proxy",
            "firstModelHash":win_model["modelHash"],
            "positionModelHash":position_model["modelHash"],
            "marginals":[{"horseNumber":no,"firstProbability":v[0],
                          "secondProbability":v[1],"thirdProbability":v[2],
                          "topThreeProbability":sum(v)} for no,v in marginal.items()],
            "orderedTopThree":podium,"normalization":total,"promotionEligible":False}


def compare_holdout(races, win_model, position_model):
    """Paired exact-order log loss; explicitly NO automatic model promotion."""
    if not races:
        raise ValueError("nonempty unseen races required")
    from .top_three_joint_research import evaluate_orders
    # evaluate_orders validates actual rank labels and computes diagnostic scores.
    baseline_preds = [predict(win_model,r) for r in races]
    baseline = evaluate_orders(baseline_preds, races)
    # Compare by mathematically equivalent prediction marginal/order structure.
    candidate = [predict_positions(position_model,win_model,r) for r in races]
    seen = set()
    totals = {"first":0.,"second":0.,"third":0.,"order":0.}
    for race,p in zip(races,candidate):
        _validate_race(race,labelled=True)
        if race["raceId"] in seen:
            raise ValueError("duplicate holdout race")
        seen.add(race["raceId"])
        numbers = {h["horseNumber"]:h["finish"] for h in race["horses"]}
        if sorted(numbers.values()) != list(range(1,len(numbers)+1)):
            raise ValueError("non-strict final order")
        actual = tuple(next(n for n,rank in numbers.items() if rank == k)
                       for k in (1,2,3))
        position = {row["horseNumber"]:row for row in p["marginals"]}
        triples = {(row["first"],row["second"],row["third"]):row["probability"]
                   for row in p["orderedTopThree"]}
        for idx,key in enumerate(("first","second","third")):
            totals[key] -= log(max(1e-15,position[actual[idx]][key+"Probability"]))
        totals["order"] -= log(max(1e-15,triples[actual]))
    count = len(races)
    return {"races":count,"baseline":baseline,
            "candidate":{"firstLogLoss":totals["first"]/count,
                         "secondPositionLogLoss":totals["second"]/count,
                         "thirdPositionLogLoss":totals["third"]/count,
                         "exactOrderLogLoss":totals["order"]/count},
            "modelSelection":"not-performed","promotionEligible":False,
            "status":"research-only-holdout-comparison"}
