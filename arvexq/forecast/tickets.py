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
    candidates = [int(row["horseNumber"]) for row in marks if row.get("mark") in {"◎", "○", "▲", "△", "☆"}]
    if len(candidates) < 2 or not probabilities.get("trifecta"):
        return []
    specs = (("馬連", 2), ("ワイド", 2), ("馬単", 2), ("3連複", 3))
    ranked = []
    for kind, size in specs:
        combos = permutations(candidates, size) if kind == "馬単" else combinations(candidates, size)
        for combo in combos:
            probability = _score(probabilities, combo, kind)
            if probability > 0:
                ranked.append((-probability, kind, combo))
    ranked.sort(key=lambda row: (row[0], row[1], row[2]))
    items = []
    for _, kind, combo in ranked[:5]:
        group = next((item for item in items if item["kind"] == kind), None)
        if group is None:
            group = {"kind": kind, "combos": [], "points": 0,
                     "reason": "Stage64全券種横断・的中確率上位5点・◎○▲△☆対象"}
            items.append(group)
        group["combos"].append(list(combo))
        group["points"] += 1
    return items
