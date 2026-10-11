from __future__ import annotations

from typing import Any

from arvexq.prediction.factor_model import MODEL_VERSION, PRIMARY_PILLARS, rank_factor_model
from arvexq.prediction.multi_head import MODEL_VERSION as MULTI_HEAD_MODEL_VERSION, attach_multi_head_signals
from arvexq.prediction.honmei_gate import evaluate_honmei_gate
from arvexq.prediction.career_readiness import attach_career_readiness

MARK_ENGINE_VERSION = "arvexq-four-pillar-marks-v8-honmei-role"
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



def sufficiently_observed_partial_career(
    detail: dict[str, Any], readiness: dict[str, Any]
) -> bool:
    """A high-coverage field may be forecast without calling ingestion complete.

    This is not a whole-career verification: it only permits an explicitly
    labelled pre-off provisional prediction if missing acquisition audits affect
    at most two runners, with several dated, usable runs for each.
    """
    from arvexq.prediction.past_performance import observed_runs

    if not isinstance(detail, dict) or detail.get("_entryOnly"):
        return False
    horses = [
        h for h in (detail.get("horses") or [])
        if isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0
        and not h.get("scratched") and not h.get("withdrawn")
        and not any(x in str(h.get("status") or "") for x in ("取消", "除外", "欠場"))
    ]
    total = len(horses)
    complete = int(readiness.get("completeHorses") or 0)
    blocked = readiness.get("blockedHorses") or []
    if total < 5 or total != int(readiness.get("activeHorses") or 0):
        return False
    # An observed, date-bounded history is usable evidence even when the
    # provider's lifetime start-count verification endpoint is unavailable.
    # This is NOT evidence of full career completeness. Require every active
    # horse to have five distinct, usable pre-race dated starts, and reject
    # contradictory counts or identity/cutoff errors.
    if complete < max(4, (4 * total + 4) // 5) or not 0 < len(blocked) <= 2:
        if len(blocked) != total:
            return False
        by_no = {int(h["horseNumber"]): h for h in horses}
        acceptable = {"provider-fetch-failed", "reported-starts-unknown"}
        for entry in blocked:
            horse = by_no.get(int(entry.get("horseNumber") or 0))
            if (not horse or not str(horse.get("name") or "").strip()
                    or entry.get("reason") not in acceptable
                    or entry.get("reportedStarts") is not None):
                return False
            try:
                runs = observed_runs(horse, detail, limit=None)
            except (ValueError, TypeError, KeyError):
                return False
            if len({str(run.get("date") or "") for run in runs}) < 5:
                return False
        return True
    by_no = {int(h["horseNumber"]): h for h in horses}
    for entry in blocked:
        horse = by_no.get(int(entry.get("horseNumber") or 0))
        if not horse or not str(horse.get("name") or "").strip():
            return False
        try:
            runs = observed_runs(horse, detail, limit=None)
        except (ValueError, TypeError, KeyError):
            return False
        if len(runs) < 3:
            return False
    return True


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

    attach_career_readiness(detail)
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    readiness = detail.get("careerReadiness") or {}
    fully_verified = readiness.get("ready") is True
    limited = not fully_verified and sufficiently_observed_partial_career(detail, readiness)
    if not fully_verified and not limited:
        for horse in horses:
            evaluation = horse.get("integratedEvaluation")
            if isinstance(evaluation, dict):
                evaluation["mark"] = ""
                evaluation.pop("rank", None)
        detail.pop("factorRanking", None)
        detail.pop("honmeiDecision", None)
        detail["predictionStatus"] = "waiting-for-full-career"
        return detail
    detail["predictionStatus"] = "partial-career-evidence" if limited else "ready"
    if limited:
        # Never set careerReadiness.ready=True or mark incomplete history complete.
        readiness["predictionEligible"] = True
        readiness["predictionEvidencePolicy"] = (
            "all-active-five-dated-observed-total-unverified-v2"
            if int(readiness.get("completeHorses") or 0) == 0
            else "80pct-verified-max2-unverified-min3-observed-v1"
        )
    ranked_rows = rank_factor_model(horses, detail)
    if not ranked_rows:
        return detail
    multi_head_summary = attach_multi_head_signals(ranked_rows)
    honmei_decision = evaluate_honmei_gate(ranked_rows, multi_head_summary, detail)
    detail["honmeiDecision"] = honmei_decision
    ranked = [row["horse"] for row in ranked_rows]
    # Publish exactly one relative ◎ when a forecast is genuinely available.
    # A failed strict podium gate downgrades reliability rather than hiding the
    # model leader; a C-grade honmei can never be treated as a fixed ticket axis.
    axis_no = int(honmei_decision.get("horseNumber") or 0)
    axis_horse = next((h for h in ranked if int(h.get("horseNumber") or 0) == axis_no), None)
    axis_rows = honmei_decision.get("axisCandidates") or []
    axis_data = next((q for q in axis_rows if q.get("horseNumber") == axis_no), {})
    grade = ("A" if honmei_decision.get("eligible") else
             "B" if float(axis_data.get("score") or 0) >= .55
             and int(axis_data.get("validRuns") or 0) >= 2 else "C")
    mh = (axis_horse or {}).get("integratedEvaluation") or {}
    axis_head = next((row.get("multiHead") or {} for row in ranked_rows
                      if row.get("horse") is axis_horse), {})
    win_head = int(axis_head.get("winRank") or 999) == 1
    gap = float((multi_head_summary or {}).get("winnerGap") or 0)
    model_winner = int((multi_head_summary or {}).get("winnerHorseNumber") or 0)
    honmei_role = "win" if win_head and model_winner == axis_no and gap >= .015 else "axis"
    honmei_decision["displayHonmei"] = axis_horse is not None
    honmei_decision["confidenceGrade"] = grade if axis_horse is not None else ""
    honmei_decision["role"] = honmei_role if axis_horse is not None else "none"
    honmei_decision["fixedAxisAllowed"] = grade in ("A", "B") and axis_horse is not None

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
        is_honmei = axis_horse is horse
        e["honmeiEligible"] = bool(honmei_decision.get("eligible") and is_honmei)
        e["honmeiRole"] = honmei_role if is_honmei else ""
        e["honmeiGrade"] = grade if is_honmei else ""
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

    # The ◎ candidate may be a 1st-place winner or a reliable podium axis.
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
        "core=four-pillar consensus + all observed pre-off career + recent-five form + relative honmei; "
        "honmei=one candidate with win/axis role and A/B/C reliability (C is not a fixed ticket axis); "
        "heads=strength(ability+record), win(ability+record+suitability+pace), "
        "upside(suitability+pace+support), market-risk(popularity-vs-model); "
        "support=pedigree+weather/going+bias+draw+body/weight+condition-change+freshness+age/sex+jockey+trainer"
    )
    return detail
