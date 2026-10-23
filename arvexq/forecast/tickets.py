"""Deterministic Stage64 ticket projection using every product mark."""
from itertools import permutations, combinations


def _score(probabilities, combo, kind):
    raw = probabilities.get("trifecta") or {}
    joint = raw if isinstance(raw, dict) else {tuple(row["combo"]): row["probability"] for row in raw}
    if kind == "馬単":
        return sum(joint.get((a, b, c), 0.0) for c in probabilities["win"] for a, b in [combo] if c not in combo)
    if kind == "3連複":
        return sum(joint.get(p, 0.0) for p in permutations(combo))
    if kind == "馬連":
        return sum(joint.get(p, 0.0) for p in permutations(combo))
    return sum(joint.get(p, 0.0) for p in permutations(combo) if set(combo).issubset(p[:3]))

def generate_tickets(prediction, marks, quoted_odds=None, min_hit_probability=0.8,
                     place_payout_slots=3):
    if not isinstance(prediction, dict) or prediction.get("predictionStatus") != "ready":
        return []
    probabilities = ((prediction.get("stages") or {}).get("probability") or {}).get("value") or {}
    candidates = [int(row["horseNumber"]) for row in marks if row.get("mark") in {"◎", "○", "▲", "△", "☆"}]
    if len(candidates) < 2 or not probabilities.get("trifecta"):
        return []
    specs = (("馬連", 2), ("ワイド", 2), ("馬単", 2), ("3連複", 3))
    items = []
    for kind, size in specs:
        combos = list(permutations(candidates, size)) if kind == "馬単" else list(combinations(candidates, size))
        ranked = sorted(combos, key=lambda c: (-_score(probabilities, c, kind), c))[:5]
        if ranked:
            items.append({"kind": kind, "combos": [list(c) for c in ranked],
                          "points": len(ranked), "reason": "Stage64確率順・◎○▲△☆全印考慮"})
    return items
