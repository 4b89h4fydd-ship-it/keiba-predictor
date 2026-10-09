"""Research-only 14-factor candidate, frozen BEFORE post.

Ranks observed fields within the same race; does not assert the percentile is
a win probability. A category uses ONE homogeneous metric across entrants:
allPastRuns speed index and m/s must NEVER be mixed.
"""
from __future__ import annotations

import hashlib
import json
from statistics import mean
from typing import Any
from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.factor_cards import FACTORS, evidence_card

VERSION = "arvexq-14-factor-shadow-v1"
CATEGORIES = (
    ("ability", ("speed", "closing", "early")),
    ("record", ("finish", "class", "form")),
    ("suitability", ("distance", "track", "going", "surface")),
    ("support", ("pedigree", "connections", "weight", "draw")),
)


def _ranks(values: list[float | None]) -> list[float | None]:
    valid = sorted(v for v in values if v is not None)
    if not valid:
        return [None for _ in values]
    if len(valid) == 1:
        return [0.5 if v is not None else None for v in values]
    return [
        None if v is None else
        (sum(x < v for x in valid) + (sum(x == v for x in valid) - 1) / 2) / (len(valid) - 1)
        for v in values
    ]


def build_factor_shadow(detail: dict[str, Any]) -> dict[str, Any]:
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)
              and h.get("horseNumber") and not is_inactive_runner(h)]
    records = [(h, evidence_card(h, detail)) for h in horses]
    # One field per factor, selected by maximum within-race availability.
    categories: dict[str, dict[str, Any]] = {}
    values: dict[str, list[float | None]] = {}
    for name, label, fields in FACTORS:
        m = [next((item for item in card["items"] if item["key"] == name), None)
             for _, card in records]
        coverage = {}
        for key in fields:
            coverage[key] = sum(any(entry.get("key") == key for entry in (x or {}).get("measurements", []))
                                for x in m)
        selected = max(fields, key=lambda k: (coverage[k], -fields.index(k)))
        raw = [
            next((float(z["value"]) for z in (x or {}).get("measurements", [])
                  if z["key"] == selected), None)
            for x in m
        ]
        categories[name] = {"label": label, "field": selected, "observed": coverage[selected]}
        values[name] = _ranks(raw)
    rows = []
    for i, (horse, card) in enumerate(records):
        factor_ranks = {key: values[key][i] for key, _, _ in FACTORS}
        families = {}
        for category, members in CATEGORIES:
            available = [factor_ranks[name] for name in members if factor_ranks[name] is not None]
            families[category] = mean(available) if available else None
        family_scores = [v for v in families.values() if v is not None]
        score = mean(family_scores) if len(family_scores) >= 3 else None
        rows.append({"horseNumber": int(horse["horseNumber"]),
                     "evidenceCount": sum(v is not None for v in factor_ranks.values()),
                     "factorRanks": factor_ranks, "families": families,
                     "researchRankScore": round(score, 8) if score is not None else None})
    eligible = [r for r in rows if r["researchRankScore"] is not None and r["evidenceCount"] >= 7]
    sufficient = len(horses) >= 3 and len(eligible) >= max(3, (len(horses) + 1) // 2)
    sorted_rows = sorted(eligible, key=lambda r: (-r["researchRankScore"], r["horseNumber"]))
    payload = {"version": VERSION, "raceId": str(detail.get("id") or ""),
               "date": str(detail.get("date") or ""),
               "model": "14-factor-equal-family-unvalidated",
               "mode": "frozen-shadow-only-not-for-betting", "sufficient": sufficient,
               "selectedFields": categories, "rows": rows,
               "candidateWinner": sorted_rows[0]["horseNumber"] if sufficient else None,
               "candidateTop3": [r["horseNumber"] for r in sorted_rows[:3]] if sufficient else [],
               "winnerProbability": None, "expectedValue": None}
    payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True,
                   ensure_ascii=False, separators=(",", ":"), default=str).encode()).hexdigest()
    return payload
