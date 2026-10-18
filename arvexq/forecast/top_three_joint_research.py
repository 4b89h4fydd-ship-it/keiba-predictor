"""Research-only internally consistent top-three order probabilities.

Plackett-Luce conditional draws from existing win probabilities. This is a
baseline ASSUMPTION, not evidence that second/third positions are calibrated.
Never supplies marks, selections, wagers or production endpoints.
"""
from __future__ import annotations

from math import isclose, isfinite, log


VERSION = "arvexq-top-three-joint-research-v1"


def joint_top_three(prediction):
    """Enumerate distinct podium orders and exact position marginals.

    Conditional P(second=j | first=i) = w_j/(sum w - w_i).
    Conditional P(third=k | i,j) = w_k/(sum w - w_i - w_j).
    Weights are the existing race-softmax *win* probabilities and NOT a
    separately fitted second/third classifier. Calculated O(n^3), bounded
    to field sizes appropriate for the existing horse-racing app.
    """
    if not isinstance(prediction, dict) or prediction.get("status") != "research-only-uncalibrated":
        raise ValueError("only uncalibrated offline win-model predictions permitted")
    rows = prediction.get("rows")
    if not isinstance(rows, list) or not 3 <= len(rows) <= 24:
        raise ValueError("complete field of 3-24 horses required")
    numbers = []
    weights = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid runner")
        n, p = row.get("horseNumber"), row.get("winProbability")
        if type(n) is not int or n <= 0 or n in numbers:
            raise ValueError("invalid or repeated horse number")
        if type(p) not in (float, int) or not isfinite(p) or p <= 0 or p > 1:
            raise ValueError("positive finite win probabilities required")
        numbers.append(n)
        weights.append(float(p))
    if not isclose(sum(weights), 1., rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("win probability distribution must sum to one")
    out = {n: [0., 0., 0.] for n in numbers}
    podium = []
    for i, a in enumerate(numbers):
        w_a = weights[i]
        remaining_after_a = 1. - w_a
        if remaining_after_a <= 0:
            raise ValueError("degenerate field")
        for j, b in enumerate(numbers):
            if i == j:
                continue
            w_b = weights[j]
            second = w_a * w_b / remaining_after_a
            after_b = remaining_after_a - w_b
            if after_b <= 0:
                raise ValueError("degenerate runner weights")
            for k, c in enumerate(numbers):
                if k in (i, j):
                    continue
                probability = second * weights[k] / after_b
                if probability <= 0 or not isfinite(probability):
                    raise ValueError("invalid podium probability")
                podium.append({"first": a, "second": b, "third": c,
                               "probability": probability})
                out[a][0] += probability
                out[b][1] += probability
                out[c][2] += probability
    total = sum(x["probability"] for x in podium)
    if not isclose(total, 1., abs_tol=1e-9):
        raise ValueError("podium distribution does not normalize")
    if any(not isclose(sum(v[i] for v in out.values()), 1., abs_tol=1e-9)
           for i in range(3)):
        raise ValueError("position marginals do not normalize")
    marginals = [{"horseNumber": n,
                  "firstProbability": out[n][0],
                  "secondProbability": out[n][1],
                  "thirdProbability": out[n][2],
                  "topThreeProbability": sum(out[n])}
                 for n in numbers]
    return {"version": VERSION, "raceId": prediction.get("raceId"),
            "status": "research-only-position-uncalibrated",
            "interpretation": "conditional-order-baseline-not-fitted-second-third-model",
            "marginals": marginals,
            "orderedTopThree": podium,
            "normalization": total,
            "promotionEligible": False}


def evaluate_orders(predictions, races):
    """Strict race-level out-of-sample position diagnostics, no selection bets.

    Each prediction must belong to its labelled race; chronology and independent
    label provenance remain requirements of the upstream verified holdout.
    """
    if not isinstance(predictions, list) or not isinstance(races, list) or len(predictions) != len(races) or not races:
        raise ValueError("matching nonempty predictions and confirmed races required")
    seen = set()
    outcomes = []
    for p, race in zip(predictions, races):
        if not isinstance(race, dict) or race.get("raceId") != p.get("raceId"):
            raise ValueError("race identity mismatch")
        if race["raceId"] in seen:
            raise ValueError("duplicate race")
        seen.add(race["raceId"])
        horses = race.get("horses")
        if not isinstance(horses, list) or len(horses) != len(p.get("rows") or []):
            raise ValueError("incomplete result field")
        finishes = {h.get("horseNumber"): h.get("finish") for h in horses}
        if (len(finishes) != len(horses) or
                {h.get("finish") for h in horses} != set(range(1, len(horses) + 1))):
            raise ValueError("strict complete results without dead heat required")
        distribution = joint_top_three(p)
        if set(finishes) != {x["horseNumber"] for x in distribution["marginals"]}:
            raise ValueError("runner identity mismatch")
        winners = [next(n for n, f in finishes.items() if f == pos) for pos in (1, 2, 3)]
        lookup = {(x["first"], x["second"], x["third"]): x["probability"]
                  for x in distribution["orderedTopThree"]}
        probs = {m["horseNumber"]: m for m in distribution["marginals"]}
        first_log = -log(max(1e-15, probs[winners[0]]["firstProbability"]))
        ordered_log = -log(max(1e-15, lookup[tuple(winners)]))
        by_first = sorted(probs, key=lambda n: (-probs[n]["firstProbability"], n))
        by_top3 = sorted(probs, key=lambda n: (-probs[n]["topThreeProbability"], n))
        outcomes.append({"firstLogLoss": first_log, "exactOrderLogLoss": ordered_log,
                         "firstHit": int(by_first[0] == winners[0]),
                         "topThreeSetHit": int(set(by_top3[:3]) == set(winners)),
                         "orderedTopThreeHit": int(tuple(by_first[:3]) == tuple(winners))})
    count = len(outcomes)
    return {"races": count, "top1Rate": sum(x["firstHit"] for x in outcomes) / count,
            "unorderedTopThreeSetRate": sum(x["topThreeSetHit"] for x in outcomes) / count,
            "orderedTopThreeRate": sum(x["orderedTopThreeHit"] for x in outcomes) / count,
            "firstLogLoss": sum(x["firstLogLoss"] for x in outcomes) / count,
            "exactOrderLogLoss": sum(x["exactOrderLogLoss"] for x in outcomes) / count,
            "status": "research-only-not-calibrated-or-certified",
            "promotionEligible": False}
