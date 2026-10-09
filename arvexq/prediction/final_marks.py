from __future__ import annotations

from typing import Any

from arvexq.prediction.factor_model import MODEL_VERSION, PRIMARY_PILLARS, rank_factor_model
from arvexq.prediction.multi_head import MODEL_VERSION as MULTI_HEAD_MODEL_VERSION, attach_multi_head_signals
from arvexq.prediction.honmei_gate import evaluate_honmei_gate

MARK_ENGINE_VERSION = "arvexq-four-pillar-marks-v7-past-context"
CORE_MARKS = ("◎", "○", "▲")
LOWER_MARKS = ("☆+", "☆", "△", "注")


def _plus_candidate(remaining_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick ☆+ from setup/upside evidence before legacy route leadership."""
    if not remaining_rows:
        return None

    upside = [r for r in remaining_rows if (r.get("multiHead") or {}).get("upsideCandidate")]
    if upside:
        upside.sort(
            key=lambda r: (
                int((r.get("multiHead") or {}).get("upsideRank") or 999),
                int((r.get("multiHead") or {}).get("winRank") or 999),
                int((r.get("horse") or {}).get("horseNumber") or 999),
            )
        )
        return upside[0]["horse"]

    routes = ("ability", "suitability", "pace", "support")
    leaders: dict[str, set[int]] = {}
    for route in routes:
        vals = [r.get(route) for r in remaining_rows if r.get(route) is not None]
        if not vals:
            leaders[route] = set()
            continue
        best = max(float(v) for v in vals)
        leaders[route] = {id(r) for r in remaining_rows if r.get(route) is not None and float(r[route]) == best}
    for row in remaining_rows:
        hits = sum(id(row) in leaders[route] for route in routes)
        if hits >= 2:
            return row["horse"]
    return None


def apply_core_marks(detail: dict[str, Any]) -> dict[str, Any]:
    """Apply final marks and persist separate ARVEXQ decision heads.

    Production core order remains the validated four-pillar v4 consensus. On top of
    that ranking we persist distinct race-relative heads for baseline strength,
    current win setup, upside and market-risk disagreement. These heads are not
    probabilities and are stored separately so later selection/backtests can learn
    which signals actually improve out-of-sample accuracy.
    """
    if not isinstance(detail, dict):
        return detail

    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    ranked_rows = rank_factor_model(horses, detail)
    if not ranked_rows:
        return detail
    multi_head_summary = attach_multi_head_signals(ranked_rows)
    honmei_decision = evaluate_honmei_gate(ranked_rows, multi_head_summary, detail)
    detail["honmeiDecision"] = honmei_decision
    ranked = [row["horse"] for row in ranked_rows]
    axis_no = int(honmei_decision.get("horseNumber") or 0) if honmei_decision.get("eligible") else 0
    axis_horse = next((h for h in ranked if int(h.get("horseNumber") or 0) == axis_no), None)

    for horse in horses:
        e = horse.setdefault("integratedEvaluation", {})
        e["legacyComputedMark"] = str(e.get("mark") or "")
        e["mark"] = ""
        e["markEngineVersion"] = MARK_ENGINE_VERSION
        e["markSource"] = "four-pillar-consensus"

    detail["factorRanking"] = []
    for row in ranked_rows:
        horse = row["horse"]
        e = horse.setdefault("integratedEvaluation", {})
        multi_head = row.get("multiHead") or {}
        evidence = {
            "rank": row["rank"],
            "dominanceScore": row["dominanceScore"],
            "scoreMeaning": "field-relative head-to-head dominance; not win probability",
            "pairwiseWins": row["pairwiseWins"],
            "pairwiseLosses": row["pairwiseLosses"],
            "pairwiseTies": row["pairwiseTies"],
            "supportTieBreakWins": row["supportTieBreakWins"],
            "pillarScores": row["pillarScores"],
            "pillarRanks": row["pillarRanks"],
            "evidenceCounts": row["evidenceCounts"],
            "evidenceFamilyCounts": row.get("evidenceFamilyCounts", {}),
            "metricRelative": row["metricRelative"],
            "rawMetrics": row["raw"],
            "sample": row["sample"],
            "multiHead": multi_head,
            "modelVersion": MODEL_VERSION,
        }
        e["coreAbilityRank"] = row["rank"]
        e["coreAbilityScore"] = row["dominanceScore"]
        e["primaryPillars"] = list(PRIMARY_PILLARS)
        e["factorEvidence"] = evidence
        e["pastPerformance"] = row.get("pastPerformance", {})
        e["careerProfile"] = row.get("careerProfile", {})
        e["multiHead"] = multi_head
        e["strengthHeadRank"] = multi_head.get("strengthRank")
        e["winHeadRank"] = multi_head.get("winRank")
        e["upsideHeadRank"] = multi_head.get("upsideRank")
        e["dangerPopular"] = bool(multi_head.get("dangerPopular"))
        e["upsideCandidate"] = bool(multi_head.get("upsideCandidate"))
        e["honmeiEligible"] = bool(honmei_decision.get("eligible") and int(horse.get("horseNumber") or 0) == int(honmei_decision.get("horseNumber") or 0))
        e["honmeiGateVersion"] = honmei_decision.get("version")
        e["podiumAxisScore"] = next((q["score"] for q in honmei_decision.get("axisCandidates", []) if q["horseNumber"] == int(horse.get("horseNumber") or 0)), None)
        horse["abilityEvidence"] = evidence
        detail["factorRanking"].append(
            {
                "horseNumber": int(horse.get("horseNumber") or 0),
                "name": horse.get("name") or "",
                **evidence,
            }
        )

    # ◎ is top-three axis, so it may differ from the winner-model leader.
    remaining_rows = [row for row in ranked_rows if row["horse"] is not axis_horse]
    core_assignments = ()
    if axis_horse is not None:
        core_assignments += (("◎", axis_horse),)
    if remaining_rows:
        core_assignments += (("○", remaining_rows.pop(0)["horse"]),)
    if remaining_rows:
        core_assignments += (("▲", remaining_rows.pop(0)["horse"]),)
    for mark, horse in core_assignments:
        horse["integratedEvaluation"]["mark"] = mark
    plus = _plus_candidate(remaining_rows)
    used: set[int] = set()
    if plus is not None:
        plus["integratedEvaluation"]["mark"] = "☆+"
        used.add(id(plus))

    leftovers = [r["horse"] for r in remaining_rows if id(r["horse"]) not in used]
    for mark, horse in zip(("☆", "△", "注"), leftovers[:3]):
        horse["integratedEvaluation"]["mark"] = mark

    mark_order = {"◎": 1, "○": 2, "▲": 3, "☆+": 4, "☆": 5, "△": 6, "注": 7}
    marked = sorted(
        ranked,
        key=lambda h: (
            mark_order.get(str((h.get("integratedEvaluation") or {}).get("mark") or ""), 99),
            int((h.get("integratedEvaluation") or {}).get("coreAbilityRank") or 999),
            int(h.get("horseNumber") or 999),
        ),
    )
    for idx, horse in enumerate(marked, 1):
        horse["integratedEvaluation"]["rank"] = idx

    detail["markEngineVersion"] = MARK_ENGINE_VERSION
    detail["predictionModelVersion"] = MODEL_VERSION
    detail["multiHeadModelVersion"] = MULTI_HEAD_MODEL_VERSION
    detail["multiHeadSummary"] = multi_head_summary
    detail["markMethod"] = (
        "core=four-pillar consensus + all observed pre-off career + recent-five form + independent top-three axis; "
        "heads=strength(ability+record), win(ability+record+suitability+pace), "
        "upside(suitability+pace+support), market-risk(popularity-vs-model); "
        "support=pedigree+weather/going+bias+draw+body/weight+condition-change+freshness+age/sex+jockey+trainer"
    )
    return detail
