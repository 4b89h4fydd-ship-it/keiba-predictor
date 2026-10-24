"""Two genuinely different fitted AI models in the existing fusion path.

ai:learned = existing regularized pairwise-ranking logistic learner.
ai:bayes   = separate categorical Naive Bayes fitted from earlier results.

Neither is claimed to represent an external company's AI or a forecaster's
actual paid opinion. Both are trained only on earlier JRA OR NAR races and
must pass independent chronological evaluation before fusion deployment.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
from math import exp, isfinite, log
import json

from arvexq.prediction.learned_scenarios import (
    fit_model, predict_model, race_evidence, race_family, VERSION as LOGISTIC_VERSION,
)
from arvexq.prediction.empirical_fusion import _timestamp
from arvexq.prediction.fusion_method_models import _order_probabilities

VERSION = "arvexq-fusion-conditional-bayes-v1"
FEATURE_KEYS = (
    "recent_win_rate", "recent_top3_rate", "same_track_finish",
    "same_distance_finish", "early_position", "closing_gain",
    "comparable_margin", "win_sampling_error",
)


def _labels(detail):
    result = detail.get("result") or {}
    if result.get("status") != "確定":
        raise ValueError("confirmed earlier results only")
    labels = {}
    for r in result.get("finishers") or []:
        if isinstance(r, dict) and type(r.get("horseNumber")) is int and type(r.get("finish")) is int:
            if r["finish"] > 0:
                labels[r["horseNumber"]] = r["finish"]
    if sum(place == 1 for place in labels.values()) != 1:
        raise ValueError("unambiguous earlier winner required")
    return labels


def _evidence(detail):
    rows = race_evidence(detail, scenario="usual")
    if len(rows) < 5 or any(not r.get("observedStarts") for r in rows):
        raise ValueError("complete preoff prior-run AI evidence required")
    nos = [r.get("horseNumber") for r in rows]
    if len(set(nos)) != len(nos) or any(type(no) is not int or no <= 0 for no in nos):
        raise ValueError("ambiguous race runner identities")
    for row in rows:
        if not isinstance(row.get("featureValues"), dict):
            raise ValueError("missing AI feature map")
    return rows


def _bin(value, thresholds):
    if value is None:
        return "missing"
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError("invalid model input feature")
    return str(sum(float(value) > boundary for boundary in thresholds))


def _quantiles(values):
    sorted_values = sorted(set(float(v) for v in values if v is not None))
    if len(sorted_values) < 4:
        return []
    return [sorted_values[(len(sorted_values)-1)*k//4] for k in (1,2,3)]


def fit_bayes(details, *, circuit, target_date, min_races=30):
    """Train class-conditional evidence likelihoods, not another logistic head."""
    if circuit not in ("中央", "地方"):
        raise ValueError("separate JRA or NAR fit required")
    dated = []
    for detail in sorted(details, key=lambda x:(x.get("date",""),x.get("id",""))):
        if detail.get("circuit") != circuit or not str(detail.get("date") or "") < target_date:
            continue
        if race_family(detail) != "flat":
            continue
        try:
            rows, labels = _evidence(detail), _labels(detail)
        except (ValueError, KeyError, TypeError):
            continue
        if not all(r["horseNumber"] in labels for r in rows):
            continue
        dated.append((detail["date"], detail["id"], rows, labels))
    if len(dated) < min_races or len({rid for _,rid,_,_ in dated}) != len(dated):
        raise ValueError("fewer than 30 independent earlier AI training races")
    distributions = {k:[] for k in FEATURE_KEYS}
    for _,_,rows,_ in dated:
        for row in rows:
            for feature in FEATURE_KEYS:
                distributions[feature].append(row["featureValues"].get(feature))
    thresholds = {k:_quantiles(vals) for k,vals in distributions.items()}
    cells = {k:{"winner":Counter(), "other":Counter()} for k in FEATURE_KEYS}
    classes = Counter()
    for _,_,rows,labels in dated:
        for row in rows:
            cl = "winner" if labels[row["horseNumber"]] == 1 else "other"
            classes[cl] += 1
            for feature in FEATURE_KEYS:
                group = _bin(row["featureValues"].get(feature), thresholds[feature])
                cells[feature][cl][group] += 1
    packed = {k:{cl:dict(sorted(vals.items())) for cl,vals in group.items()}
              for k,group in cells.items()}
    model = {
        "version": VERSION, "circuit": circuit, "family": "flat",
        "trainingThrough": max(date for date,_,_,_ in dated),
        "trainingRaceIds": [rid for _,rid,_,_ in dated],
        "trainingRaceCount": len(dated), "classes": dict(classes),
        "quantileThresholds": thresholds, "counts": packed,
        "features": list(FEATURE_KEYS), "laplaceAlpha": .5,
        "calibrationStatus": "needs-independent-walk-forward",
    }
    model["modelHash"] = sha256(json.dumps(model, sort_keys=True,
                                 ensure_ascii=False).encode()).hexdigest()
    return model


def predict_bayes(detail, model, *, captured_at, scheduled_off_at):
    if _timestamp(captured_at) >= _timestamp(scheduled_off_at):
        raise ValueError("post-off AI inference forbidden")
    if (detail.get("result") or {}).get("finishers") or (detail.get("result") or {}).get("payouts"):
        raise ValueError("target result leakage")
    if model.get("version") != VERSION or model.get("circuit") != detail.get("circuit"):
        raise ValueError("cross-circuit or incompatible Bayesian AI")
    if model.get("trainingThrough", "") >= detail.get("date", ""):
        raise ValueError("future-trained AI cannot predict earlier race")
    source = {k:v for k,v in model.items() if k!="modelHash"}
    expected = sha256(json.dumps(source, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if expected != model.get("modelHash"):
        raise ValueError("Bayesian model artifact hash mismatch")
    rows = _evidence(detail)
    counts = model["classes"]
    w, o = counts["winner"], counts["other"]
    if w < 30 or o < 30:
        raise ValueError("insufficient independent winners/losers")
    logits = {}
    for row in rows:
        # Bayesian likelihood ratios are empirically learned per training
        # feature, not subjective multipliers for any jockey/horse.
        score = log((w + .5)/(o + .5))
        for feature in FEATURE_KEYS:
            group = _bin(row["featureValues"].get(feature), model["quantileThresholds"][feature])
            cells = model["counts"][feature]
            categories = len(model["quantileThresholds"][feature])+2
            num_w = cells["winner"].get(group,0) + .5
            num_o = cells["other"].get(group,0) + .5
            score += log(num_w/(w+.5*categories)) - log(num_o/(o+.5*categories))
        logits[row["horseNumber"]] = score
    top = max(logits.values())
    scores = {no:exp(max(-60., min(0., val-top))) for no,val in logits.items()}
    win, top3, triples = _order_probabilities(sorted(scores), scores)
    return {
        "modelVersion": "ai:bayes/" + model["modelHash"][:16],
        "evidenceId": sha256(json.dumps([detail["id"], model["modelHash"],
                    captured_at], ensure_ascii=False).encode()).hexdigest(),
        "raceId": detail["id"], "capturedAt": captured_at,
        "win": win, "top3": top3, "trifecta": triples,
        "sourceKind": "independently-fitted-naive-bayes",
        "modelTrainingThrough": model["trainingThrough"],
    }


def predict_logistic(detail, model, *, captured_at, scheduled_off_at):
    """Reuse the registered learned_scenarios system, never retrain on target."""
    if _timestamp(captured_at) >= _timestamp(scheduled_off_at):
        raise ValueError("post-off AI inference forbidden")
    if (detail.get("result") or {}).get("finishers") or (detail.get("result") or {}).get("payouts"):
        raise ValueError("target result leakage")
    if model.get("version") != LOGISTIC_VERSION:
        raise ValueError("wrong logistic AI artifact")
    response = predict_model(detail, model)
    cases = response.get("scenarios") or []
    usual = next((x for x in cases if x.get("id")=="usual"), None)
    if not usual or not isinstance(usual.get("probabilities"), dict):
        raise ValueError("no complete earlier-trained logistic scenario")
    probs = usual["probabilities"]
    joint = [{"combo": event["order"][:3], "probability": event["probability"]}
             for event in usual["orders"]]
    return {
        "modelVersion": "ai:learned/" + model["modelHash"][:16],
        "evidenceId": sha256(json.dumps([detail["id"], model["modelHash"],
                   captured_at], ensure_ascii=False).encode()).hexdigest(),
        "raceId": detail["id"], "capturedAt": captured_at,
        "win": {int(no):row["win"] for no,row in probs.items()},
        "top3": {int(no):row["top3"] for no,row in probs.items()},
        "trifecta": joint, "sourceKind": "existing-pairwise-trained-logistic",
        "modelTrainingThrough": model["training"]["lastDate"],
    }


def fit_two_ais(details, *, circuit, target_date, min_races=30):
    eligible = [d for d in details if d.get("circuit")==circuit and
                str(d.get("date") or "") < target_date and
                (d.get("result") or {}).get("status")=="確定"]
    logistic = fit_model(eligible, circuit=circuit)
    bayes = fit_bayes(eligible, circuit=circuit,
                      target_date=target_date, min_races=min_races)
    if logistic["training"]["lastDate"] >= target_date:
        raise ValueError("future labels used in logistic training")
    return {"ai:learned":logistic,"ai:bayes":bayes}
