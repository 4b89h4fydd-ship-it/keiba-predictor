"""Daily strict race triage (36-race illustration is a pool, not a quota).

All thresholds are unfitted and the output is research-only; they must
not become published recommendations without a frozen, paired test.
"""
from __future__ import annotations


def select_daily_races(records: list[dict], *, min_coverage=60,
                       min_place_gap=0.04) -> dict:
    """Select races with two place-capable heads and no invented exclusion.

    Input: [{"raceId": ..., "masterAnalysis": {...}}, ...].
    A "dangerous popular" flag is an *evaluation* exclusion candidate,
    never a removal from the race or the probability distribution.
    """
    evaluated = []
    seen = set()
    for rec in records:
        rid = str(rec.get("raceId") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        data = rec.get("masterAnalysis") or {}
        rows = data.get("runners") or []
        reasons = []
        if data.get("status") != "shadow-candidate":
            reasons.append("master-evidence-unavailable")
        if data.get("marketStatus") != "complete":
            reasons.append("no-complete-observed-market")
        if not rows:
            reasons.append("no-runner-scores")
        coverage = (sum(r.get("coveragePoints") or 0 for r in rows) / len(rows)
                    if rows else 0.0)
        if coverage < min_coverage:
            reasons.append("low-feature-coverage")
        pace = data.get("pace") or {}
        if pace.get("unknown"):
            reasons.append("unknown-pace-runners")
        place = sorted(
            (r for r in rows if isinstance(r.get("pTop3"), (int, float))),
            key=lambda r: (-r["pTop3"], r["horseNumber"]))
        heads = [r["horseNumber"] for r in place[:2]]
        gap = (place[1]["pTop3"] - place[2]["pTop3"]
               if len(place) >= 3 else None)
        if gap is None or gap < min_place_gap:
            reasons.append("two-head-gap-not-confirmed")
        risky = [r.get("horseNumber") for r in rows
                 if r.get("popularRisk") == "C-candidate"]
        if any(n in risky for n in heads):
            reasons.append("top-head-market-contradiction")
        evaluated.append({
            "raceId": rid,
            "selected": not reasons,
            "headCandidates": heads,
            "avoidHypotheses": risky,
            "coveragePoints": round(coverage, 2),
            "twoHeadPlaceGap": round(gap, 4) if gap is not None else None,
            "reasons": reasons,
            "selectionStatus": "unfitted-shadow-criterion",
        })
    shortlisted = [r for r in evaluated if r["selected"]]
    shortlisted.sort(key=lambda r: (
        -(r["twoHeadPlaceGap"] or 0), -r["coveragePoints"], r["raceId"]))
    return {
        "inputRaces": len(records),
        "evaluatedRaces": len(evaluated),
        "selectedCount": len(shortlisted),
        "selected": shortlisted,
        "allDecisions": evaluated,
        "status": "research-only-not-purchase-advice",
        "note": "No fixed 36-race quota, no auto-deletion of excluded horse",
    }
