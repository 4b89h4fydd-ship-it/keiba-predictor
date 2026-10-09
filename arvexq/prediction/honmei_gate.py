from __future__ import annotations

from typing import Any
from arvexq.prediction.career_evidence import career_rates

GATE_VERSION = "arvexq-podium-axis-gate-v5"
PRIMARY_PILLARS = ("ability", "record", "suitability", "pace")


def _iv(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _fv(v: Any, default: float = 0.0) -> float:
    try:
        out = float(v)
        return out if out == out and abs(out) != float("inf") else default
    except (TypeError, ValueError):
        return default


def _historical_top3(horse: dict[str, Any]) -> tuple[int, int, float]:
    runs = horse.get("recentRaces") or horse.get("allPastRuns") or []
    count = top3 = 0
    for run in runs[:5]:
        if not isinstance(run, dict):
            continue
        finish = _iv(run.get("finish") or run.get("finishPosition") or run.get("rank"))
        field = _iv(run.get("fieldSize"))
        if field < 2 or finish <= 0 or finish > field:
            continue
        count += 1
        top3 += int(finish <= 3)
    return count, top3, (top3 + .5) / (count + 1)


def evaluate_honmei_gate(
    ranked_rows: list[dict[str, Any]],
    multi_head_summary: dict[str, Any] | None,
    race: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Independent top-three betting-axis gate. Scores are not hit probabilities.

    Use actual pre-race evidence, not odds or the win-only ranking. Do not
    force a selection when top-three consistency or separation is weak.
    """
    if len(ranked_rows) < 2:
        return {"version": GATE_VERSION, "eligible": False, "horseNumber": 0,
                "reason": "insufficient-field", "failed": ["field"]}
    circuit = str((race or {}).get("circuit") or "")
    central = circuit in {"中央", "JRA"}
    field = len(ranked_rows)
    options: list[dict[str, Any]] = []
    for row in ranked_rows:
        h = row.get("horse") or {}
        families = row.get("evidenceFamilyCounts") or {}
        pillar_ranks = row.get("pillarRanks") or {}
        values = [row.get(p) for p in PRIMARY_PILLARS]
        coverage = sum(v is not None for v in values)
        mean_pillar = sum(_fv(v) for v in values if v is not None) / max(1, coverage)
        mh = row.get("multiHead") or {}
        nr, n3, recent_score = _historical_top3(h)
        strength = max(0., min(1., _fv(mh.get("strengthScore"))))
        spread = max(values) - min(values) if coverage == 4 else 1.
        relative_rank = 1. - (max(1, _iv(row.get("rank"), field)) - 1) / max(1, field - 1)
        # Top-three repeatability outranks single-win dominance, especially
        # when a small field exaggerates differences in ordinal factor rank.
        score = (.38 * recent_score + .12 * relative_rank + .25 * mean_pillar
                 + .15 * strength + .10 * (1. - max(0., min(1., spread))))
        option = {
            "horseNumber": _iv(h.get("horseNumber")), "score": round(score, 6),
            "factorRank": _iv(row.get("rank"), 999),
            "strengthRank": _iv(mh.get("strengthRank"), 999),
            "winRank": _iv(mh.get("winRank"), 999),
            "sample": _iv(row.get("sample")), "coverage": coverage,
            "families": sum(_iv(families.get(p)) for p in PRIMARY_PILLARS),
            "paceFamilies": _iv(families.get("pace")),
            "pillarSupport": sum(_iv(pillar_ranks.get(p), 999) <= min(field, 5) for p in PRIMARY_PILLARS),
            "careerHistory": career_rates(h, str((race or {}).get("date") or "")),
            "validRuns": nr, "recentTop3": n3,
            "recentTop3Rate": n3 / nr if nr else 0.,
            "evidenceFamilies": {p: _iv(families.get(p)) for p in PRIMARY_PILLARS},
        }
        options.append(option)
    options.sort(key=lambda x: (-x["score"], x["factorRank"], x["horseNumber"]))
    winner, next_horse = options[:2]
    gap = winner["score"] - next_horse["score"]
    families = winner["evidenceFamilies"]
    checks = {
        "qualifiedRunner": winner["horseNumber"] > 0,
        "abilitySupported": winner["factorRank"] <= 2 and winner["strengthRank"] <= 3,
        "winnerCandidateSupported": winner["winRank"] <= 3,
        "completePillars": winner["coverage"] == 4 and winner["pillarSupport"] >= 3,
        # Two starts with one placing were previously enough for the axe;
        # require multiple independently observed podium finishes instead.
        "historicalPodium": (
            winner["validRuns"] >= 3 and winner["recentTop3"] >= 2
            and winner["recentTop3Rate"] >= .60
            and (winner["validRuns"] < 5 or winner["recentTop3"] >= 3)
        ),
        "evidenceDepth": winner["sample"] >= 3 and winner["families"] >= 9
                         and winner["paceFamilies"] >= 2,
        "axisScore": winner["score"] >= .62,
        "axisSeparation": gap >= .03,
    }
    if central:
        checks["centralHistory"] = winner["validRuns"] >= 3
        checks["centralEvidence"] = (winner["families"] >= 9
                                    and families["ability"] >= 2
                                    and families["record"] >= 2
                                    and families["pace"] >= 2)
    failed = [k for k, ok in checks.items() if not ok]
    return {
        "version": GATE_VERSION, "eligible": not failed,
        "horseNumber": winner["horseNumber"],
        "reason": "podium-axis-passed" if not failed else "axis-withheld",
        "checks": checks, "failed": failed,
        "axisScore": winner["score"], "runnerUpAxisScore": next_horse["score"],
        "axisMargin": round(gap, 6),
        "axisMeaning": "relative-top3-axis-strength-not-hit-probability",
        "selectionPolicy": "conservative-podium-crosscheck-v1-not-calibrated",
        "axisCandidates": options[:5], "circuit": circuit,
        "allCareerEvidencePolicy": "dated-only-before-race-audit-not-yet-calibrated-for-rank",
    }
