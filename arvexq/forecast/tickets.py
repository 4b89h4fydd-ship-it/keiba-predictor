"""Deterministic Stage64 ticket projection using every product mark."""
from itertools import permutations, combinations
from math import isfinite


def _score(probabilities, combo, kind):
    raw = probabilities.get("trifecta") or {}
    joint = raw if isinstance(raw, dict) else {tuple(row["combo"]): row["probability"] for row in raw}
    # Stage64 stores probabilities for ordered 1st/2nd/3rd triples.
    # Project that existing joint distribution to each wager's finish rule;
    # pair tickets must never look up a nonexistent two-element joint key.
    if kind == "馬単":
        return sum(p for finish, p in joint.items() if finish[:2] == tuple(combo))
    if kind == "馬連":
        return sum(p for finish, p in joint.items() if set(finish[:2]) == set(combo))
    if kind == "ワイド":
        return sum(p for finish, p in joint.items() if set(combo).issubset(finish[:3]))
    if kind == "3連複":
        return sum(p for finish, p in joint.items() if set(finish[:3]) == set(combo))
    raise ValueError("unknown wager kind")


def _kochi_final_triples(joint):
    """Five research candidates from the pre-off joint order distribution.

    Every active runner in the model is eligible, including unmarked third-
    place candidates. Three trio and two trifecta candidates use distinct
    events where possible; no actual race results or post-off odds are read.
    The 3:2 allocation is a fixed uncalibrated policy, not an EV optimum.
    """
    trio_mass = {}
    ordered_mass = {}
    for raw_combo, raw_probability in joint.items():
        try:
            combo = tuple(int(n) for n in raw_combo)
            probability = float(raw_probability)
        except (ValueError, TypeError):
            return []
        if (len(combo) != 3 or len(set(combo)) != 3
                or any(n <= 0 for n in combo)
                or not isfinite(probability) or probability < 0):
            return []
        unordered = tuple(sorted(combo))
        trio_mass[unordered] = trio_mass.get(unordered, 0.) + probability
        ordered_mass[combo] = ordered_mass.get(combo, 0.) + probability
    if not ordered_mass or not isfinite(sum(ordered_mass.values())) or sum(ordered_mass.values()) <= 0:
        return []
    ranked_trios = sorted(trio_mass, key=lambda c: (-trio_mass[c], c))
    ranked_trifectas = sorted(ordered_mass, key=lambda c: (-ordered_mass[c], c))
    trios = ranked_trios[:3]
    covered_trios = set(trios)
    # With no authenticated trifecta prices, avoid spending all two ordered
    # slots on finishes already covered by the three unordered tickets.
    complement = [c for c in ranked_trifectas if tuple(sorted(c)) not in covered_trios]
    trifectas = (complement + [c for c in ranked_trifectas if c not in complement])[:2]
    if not trios or not trifectas:
        return []
    return [
        {"kind": "3連複", "combos": [list(c) for c in trios], "points": len(trios),
         "reason": "高知ファイナル：発走前の全出走馬の着順分布から選定（未校正・期待値未検証）"},
        {"kind": "3連単", "combos": [list(c) for c in trifectas], "points": len(trifectas),
         "reason": "高知ファイナル：3連複と重複する着順を可能な範囲で除外（未校正・期待値未検証）"},
    ]


def generate_tickets(prediction, marks, quoted_odds=None, min_hit_probability=0.8,
                     place_payout_slots=3, race=None):
    from arvexq.prediction.empirical_fusion import VERSION as FUSION_VERSION
    if isinstance(prediction, dict) and prediction.get("modelVersion") == FUSION_VERSION:
        # Same pre-off empirical model and authenticated quoted prices supply
        # the only tickets. No Stage64 or subjective recalculation.
        if prediction.get("predictionStatus") != "ready":
            return []
        sealed = prediction.get("recommendedBets")
        if not isinstance(sealed, list) or sum(len(t.get("combos") or [])
                for t in sealed if isinstance(t, dict)) > 5:
            return []
        return [dict(t, combos=[list(c) for c in t["combos"]])
                for t in sealed if isinstance(t, dict) and
                t.get("kind") in ("馬連", "ワイド", "馬単", "3連複", "3連単")
                and isinstance(t.get("combos"), list)]

    if not isinstance(prediction, dict) or prediction.get("predictionStatus") != "ready":
        return []
    probabilities = ((prediction.get("stages") or {}).get("probability") or {}).get("value") or {}
    candidates_horses = [int(row["horseNumber"]) for row in marks if row.get("mark") in {"◎", "○", "▲", "△", "☆"}]
    if len(candidates_horses) < 2 or not probabilities.get("trifecta"):
        return []
    specs = (("馬連", 2), ("ワイド", 2), ("馬単", 2), ("3連複", 3))
    # One Stage64 joint finishing-order distribution owns the entire ticket
    # decision. Maximize the probability that *at least one* of the ~5 bets
    # hits, rather than simply buying five overlapping high-marginal tickets.
    # This is an uncalibrated model comparison, not a measured hit-rate claim.
    raw = probabilities["trifecta"]
    joint = raw if isinstance(raw, dict) else {
        tuple(row["combo"]): row["probability"] for row in raw
    }
    if (isinstance(race, dict) and race.get('track') == '高知'
            and 'ファイナル' in str(race.get('title') or '')):
        return _kochi_final_triples(joint)
    finishes = list(joint.items())
    def matches(finish, combo, kind):
        if kind == "馬単":
            return finish[:2] == tuple(combo)
        if kind == "馬連":
            return set(finish[:2]) == set(combo)
        if kind == "ワイド":
            return set(combo).issubset(finish[:3])
        return kind == "3連複" and set(finish[:3]) == set(combo)
    specs = (("馬連", 2), ("ワイド", 2), ("馬単", 2), ("3連複", 3))
    candidates = []
    for kind, size in specs:
        combos = permutations(candidates_horses, size) if kind == "馬単" else combinations(candidates_horses, size)
        for combo in combos:
            covered = frozenset(i for i, (finish, _) in enumerate(finishes)
                                if matches(finish, combo, kind))
            if covered:
                candidates.append((kind, tuple(combo), covered))
    selected = []
    covered = set()
    while candidates and len(selected) < 5:
        # Probability of uncovered winning outcomes is the new coverage.
        # Marginal ticket probability breaks ties, then stable identity.
        ranked = sorted(candidates, key=lambda item: (
            -sum(finishes[i][1] for i in item[2] if i not in covered),
            -sum(finishes[i][1] for i in item[2]),
            item[0], item[1]))
        chosen = ranked[0]
        marginal = sum(finishes[i][1] for i in chosen[2] if i not in covered)
        if marginal <= 1e-12:
            break
        selected.append(chosen)
        covered.update(chosen[2])
        candidates.remove(chosen)
    items = []
    for kind, combo, _ in selected:
        group = next((item for item in items if item["kind"] == kind), None)
        if group is None:
            group = {"kind": kind, "combos": [], "points": 0,
                     "reason": "同一Stage64の着順分布から重複的中を除いて選定（未校正）"}
            items.append(group)
        group["combos"].append(list(combo))
        group["points"] += 1
    return items
