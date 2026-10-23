"""Deterministic Stage64 ticket projection using every product mark."""
from itertools import permutations, combinations


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

def generate_tickets(prediction, marks, quoted_odds=None, min_hit_probability=0.8,
                     place_payout_slots=3):
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
