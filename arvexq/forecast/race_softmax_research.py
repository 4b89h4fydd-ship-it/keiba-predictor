"""Independent, research-only per-race win probability learner.

This is NOT an approved production predictor. Marks, tickets, fallback scores
and result-dependent feature reconstruction are deliberately absent.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from hashlib import sha256
from math import exp, isfinite, log, sqrt
import json
import re

VERSION = "arvexq-race-softmax-research-v1"
STATIC = frozenset(("age", "carried_weight", "body_weight",
                    "body_weight_change", "days_since_last", "distance",
                    "frame_number"))
BANNED = ("market::", "current::", "result::", "target::", "label::",
          "outcome::", "payout::", "postrace::")


def _digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


_HISTORY = re.compile(
    r"history::(?:all|same_track|same_surface|same_condition|same_track_surface|"
    r"matched_clock_context|same_surface_condition|(?:same_track_|same_surface_)?distance_(?:100|200|400))"
    r"::w(?:1|3|5|10|all)::"
    r"(?:run_count|(?:finish_quality|win_flag|top2_flag|top3_flag|speed|clock_speed|"
    r"early_speed|late_speed|position_quality|opponent_level|prize|margin|carried_weight|"
    r"body_weight|distance)::(?:count|mean|median|max|min|last|std|q25|q75|trend|"
    r"latest_minus_mean|latest_minus_median|range))"
)
_DELTA = re.compile(
    r"delta::(?:same_track|same_surface|same_condition|distance_200|"
    r"same_surface_distance_200|same_track_distance_200)_minus_"
    r"(?:all|same_track|same_surface)::(?:finish_quality|speed|late_speed|"
    r"position_quality|opponent_level)::w5"
)
_RELATIVE = re.compile(
    r"relative::(.+)::(?:percentile|field_mean_delta|leader_gap|zscore)"
)


def _allowed_feature(key):
    if not isinstance(key, str) or any(block in key.lower() for block in BANNED):
        return False
    if key.startswith("static::"):
        return key[len("static::"):] in STATIC
    if _HISTORY.fullmatch(key) or _DELTA.fullmatch(key):
        return True
    match = _RELATIVE.fullmatch(key)
    return bool(match and (_HISTORY.fullmatch(match.group(1))
                           or _DELTA.fullmatch(match.group(1))
                           or match.group(1).startswith("static::")
                           and match.group(1)[len("static::"):] in STATIC))


def _validate_race(race, *, labelled):
    """Require full-field, strictly earlier, traceable pre-off observations.

    Dates and timestamps must come from independent capture evidence. An
    archive reconstructed after a race cannot be certified by this function.
    """
    if not isinstance(race, dict):
        raise ValueError("race must be a mapping")
    rid, day = str(race.get("raceId") or ""), str(race.get("date") or "")
    if not rid or date.fromisoformat(day).isoformat() != day:
        raise ValueError("raceId and ISO date required")
    if race.get("circuit") not in ("中央", "地方"):
        raise ValueError("unknown circuit")
    if race.get("family") not in ("flat", "jumps", "banei"):
        raise ValueError("race family required")
    captured, post = race.get("capturedAtEpoch"), race.get("postAtEpoch")
    if (not isinstance(captured, int) or isinstance(captured, bool)
            or not isinstance(post, int) or isinstance(post, bool)
            or captured <= 0 or captured >= post):
        raise ValueError("independently captured pre-off timestamp required")
    jst = timezone(timedelta(hours=9))
    if datetime.fromtimestamp(post, jst).date().isoformat() != day:
        raise ValueError("scheduled post date differs from race date")
    if not isinstance(race.get("snapshotHash"), str) or len(race["snapshotHash"]) < 16:
        raise ValueError("immutable snapshot identity required")
    horses = race.get("horses")
    if not isinstance(horses, list) or len(horses) < 3:
        raise ValueError("full field of three or more horses required")
    declared = race.get("declaredHorseNumbers")
    if (not isinstance(declared, list) or len(declared) != len(horses)
            or any(type(n) is not int or n <= 0 for n in declared)
            or len(set(declared)) != len(declared)):
        raise ValueError("external active-runner roster required")
    numbers = set()
    winners = 0
    for horse in horses:
        if not isinstance(horse, dict):
            raise ValueError("horse must be a mapping")
        number = horse.get("horseNumber")
        if type(number) is not int or number <= 0 or number in numbers:
            raise ValueError("duplicate or invalid horse number")
        numbers.add(number)
        if any(horse.get(key) for key in ("scratched", "withdrawn", "cancelled")):
            raise ValueError("non-runner present in active field")
        features = horse.get("features")
        if not isinstance(features, dict):
            raise ValueError("horse feature mapping required")
        for key, value in features.items():
            if not _allowed_feature(key):
                raise ValueError("unsupported or leaky feature: " + str(key))
            if type(value) not in (float, int) or not isfinite(value):
                raise ValueError("finite numeric features required")
        if labelled:
            finish = horse.get("finish")
            if type(finish) is not int or finish <= 0 or finish > len(horses):
                raise ValueError("complete positive finish labels required")
            winners += int(finish == 1)
    if numbers != set(declared):
        raise ValueError("active runners do not match the declared roster")
    if labelled and winners != 1:
        raise ValueError("exactly one winner required (dead heats need a separate model)")
    return race


def _split(races):
    """Split by entire chronological DAYS; tune nothing using test labels."""
    ordered = sorted(races, key=lambda r: (r["date"], r["raceId"]))
    days = sorted({r["date"] for r in ordered})
    if len(days) < 5:
        raise ValueError("at least five different historical dates required")
    a = max(2, int(len(days) * .60))
    b = max(a + 1, int(len(days) * .80))
    if b >= len(days):
        b = len(days) - 1
    train_days, valid_days, test_days = set(days[:a]), set(days[a:b]), set(days[b:])
    return ([r for r in ordered if r["date"] in train_days],
            [r for r in ordered if r["date"] in valid_days],
            [r for r in ordered if r["date"] in test_days])


def _softmax(values):
    high = max(values)
    e = [exp(max(-50., value - high)) for value in values]
    total = sum(e)
    return [v / total for v in e]


def _vector(horse, model):
    values = horse["features"]
    return [max(-6., min(6., (values.get(name, model["means"][i]) - model["means"][i])
                               / model["scales"][i]))
            for i, name in enumerate(model["features"])]


def train(train_races, *, epochs=250, learning_rate=.08, ridge=.02, max_features=48):
    """Fit multinomial race cross-entropy; all scaling and selection use train only."""
    if not train_races or type(epochs) is not int or not 1 <= epochs <= 2000:
        raise ValueError("nonempty train races and 1-2000 epochs required")
    if not (0 < learning_rate <= .5 and 0 <= ridge <= 1 and 1 <= max_features <= 256):
        raise ValueError("invalid optimizer configuration")
    seen = set()
    circuit = train_races[0]["circuit"]
    family = train_races[0]["family"]
    for race in train_races:
        _validate_race(race, labelled=True)
        if race["raceId"] in seen:
            raise ValueError("duplicate training race")
        seen.add(race["raceId"])
        if race["circuit"] != circuit or race["family"] != family:
            raise ValueError("separate circuit and family models required")
    # Count by race, not by horse; only train-set feature frequencies determine selection.
    counts = {}
    for race in train_races:
        for key in {k for h in race["horses"] for k in h["features"]}:
            counts[key] = counts.get(key, 0) + 1
    features = sorted(counts, key=lambda k: (-counts[k], k))[:max_features]
    if not features:
        raise ValueError("no approved pre-race features")
    # Missingness is kept as separate indicators; do not interpret it as a zero run.
    rows = [h for r in train_races for h in r["horses"]]
    means, scales = [], []
    for key in features:
        obs = [float(h["features"][key]) for h in rows if key in h["features"]]
        mean = sum(obs) / len(obs) if obs else 0.
        sd = sqrt(sum((v - mean) ** 2 for v in obs) / len(obs)) if obs else 1.
        means.append(mean)
        scales.append(max(sd, 1e-6))
    model = {"version": VERSION, "circuit": circuit, "family": family,
             "trainedThrough": max(r["date"] for r in train_races),
             "trainedRaceIds": sorted(seen), "features": features,
             "means": means, "scales": scales, "weights": [0.] * (2 * len(features)),
             "trainingRaces": len(train_races), "trainingInputHash": _digest(train_races),
             "status": "research-not-calibrated-not-production",
             "optimizer": {"epochs": epochs, "learningRate": learning_rate, "ridge": ridge}}
    def vector(h):
        base = _vector(h, model)
        missing = [float(k not in h["features"]) for k in features]
        return base + missing
    weights = model["weights"]
    for _ in range(epochs):
        grad = [ridge * w for w in weights]
        for race in train_races:
            xs = [vector(h) for h in race["horses"]]
            probs = _softmax([sum(w * x for w, x in zip(weights, row)) for row in xs])
            for h, x, p in zip(race["horses"], xs, probs):
                err = p - float(h["finish"] == 1)
                for i, v in enumerate(x):
                    grad[i] += err * v / len(train_races)
        weights = [max(-20., min(20., w - learning_rate * g)) for w, g in zip(weights, grad)]
    model["weights"] = weights
    model["modelHash"] = _digest(model)
    return model


def predict(model, race):
    _validate_race(race, labelled=False)
    if model.get("version") != VERSION or model.get("modelHash") != _digest(
            {k: v for k, v in model.items() if k != "modelHash"}):
        raise ValueError("invalid model integrity or version")
    if race["circuit"] != model["circuit"] or race["family"] != model["family"]:
        raise ValueError("cross-circuit/family prediction prohibited")
    if race["date"] <= model["trainedThrough"] or race["raceId"] in model["trainedRaceIds"]:
        raise ValueError("train/lookahead leakage: prediction must be later than training")
    count = len(model["features"])
    if len(model["weights"]) != 2 * count or len(model["means"]) != count or len(model["scales"]) != count:
        raise ValueError("invalid model dimensions")
    if not all(isfinite(x) for key in ("means", "scales", "weights") for x in model[key]):
        raise ValueError("non-finite model parameters")
    if min(model["scales"]) <= 0:
        raise ValueError("invalid scales")
    vectors = []
    for horse in race["horses"]:
        base = _vector(horse, model)
        vectors.append(base + [float(k not in horse["features"]) for k in model["features"]])
    scores = [sum(w * x for w, x in zip(model["weights"], xs)) for xs in vectors]
    probabilities = _softmax(scores)
    return {"version": VERSION, "modelHash": model["modelHash"],
            "status": "research-only-uncalibrated", "raceId": race["raceId"],
            "rows": [{"horseNumber": h["horseNumber"], "winProbability": p}
                     for h, p in zip(race["horses"], probabilities)]}


def evaluate(model, races):
    """Predefined out-of-sample metrics, not mark/ticket hit rates."""
    losses, baseline, brier, wins, top3, total = [], [], [], 0, 0, 0
    for race in races:
        _validate_race(race, labelled=True)
        predicted = predict(model, race)["rows"]
        p = {row["horseNumber"]: row["winProbability"] for row in predicted}
        winner = next(h["horseNumber"] for h in race["horses"] if h["finish"] == 1)
        losses.append(-log(max(1e-12, p[winner])))
        baseline.append(log(len(race["horses"])))
        ranked = sorted(p, key=lambda n: (-p[n], n))
        wins += int(ranked[0] == winner)
        top3 += int(winner in ranked[:3])
        brier.append(sum((p[h["horseNumber"]] - float(h["finish"] == 1)) ** 2
                         for h in race["horses"]) / len(race["horses"]))
        total += 1
    if not total:
        raise ValueError("nonempty labelled holdout required")
    return {"races": total, "raceLogLoss": sum(losses) / total,
            "uniformRaceLogLoss": sum(baseline) / total,
            "runnerBrier": sum(brier) / total, "top1Rate": wins / total,
            "top3CaptureRate": top3 / total, "modelStatus": "research-only"}


def chronological_experiment(races, **settings):
    """Fixed 60/20/20 date split; test untouched by training and validation."""
    if not isinstance(races, list):
        raise ValueError("race list required")
    seen = set()
    for race in races:
        _validate_race(race, labelled=True)
        if race["raceId"] in seen:
            raise ValueError("duplicate race identity")
        seen.add(race["raceId"])
    train_set, validation, test = _split(races)
    model = train(train_set, **settings)
    if any(r["circuit"] != model["circuit"] or r["family"] != model["family"] for r in races):
        raise ValueError("train JRA/NAR and flat/jumps/banei independently")
    return {"version": VERSION, "model": model,
            "split": {"train": len(train_set), "validation": len(validation), "test": len(test),
                      "trainedThrough": model["trainedThrough"],
                      "testDates": sorted({r["date"] for r in test})},
            "validation": evaluate(model, validation), "test": evaluate(model, test),
            "promotionEligible": False}
