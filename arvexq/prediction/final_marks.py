from __future__ import annotations

from typing import Any

from arvexq.prediction.factor_model import MODEL_VERSION, PRIMARY_PILLARS, rank_factor_model

MARK_ENGINE_VERSION = "arvexq-four-pillar-marks-v4"
CORE_MARKS = ("◎", "○", "▲")
LOWER_MARKS = ("☆+", "☆", "△", "注")


def _plus_candidate(remaining_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick ☆+ only when one remaining horse leads multiple upside routes."""
    if not remaining_rows:
        return None
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
    """Apply final marks from the ARVEXQ four-pillar consensus model.

    Primary order is ability, record, suitability and pace by head-to-head majority.
    Pedigree, weather/going response, same-day bias, draw, body/weight context,
    condition changes, freshness, jockey and trainer resolve close primary ties.
    """
    if not isinstance(detail, dict):
        return detail

    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    ranked_rows = rank_factor_model(horses, detail)
    if not ranked_rows:
        return detail
    ranked = [row["horse"] for row in ranked_rows]

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
            "metricRelative": row["metricRelative"],
            "rawMetrics": row["raw"],
            "sample": row["sample"],
            "modelVersion": MODEL_VERSION,
        }
        e["coreAbilityRank"] = row["rank"]
        e["coreAbilityScore"] = row["dominanceScore"]
        e["primaryPillars"] = list(PRIMARY_PILLARS)
        e["factorEvidence"] = evidence
        horse["abilityEvidence"] = evidence
        detail["factorRanking"].append(
            {
                "horseNumber": int(horse.get("horseNumber") or 0),
                "name": horse.get("name") or "",
                **evidence,
            }
        )

    for mark, horse in zip(CORE_MARKS, ranked[:3]):
        horse["integratedEvaluation"]["mark"] = mark

    remaining_rows = ranked_rows[3:]
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
    detail["markMethod"] = (
        "primary=ability+record+suitability+pace majority; "
        "support=pedigree+weather/going+bias+draw+body/weight+condition-change+freshness+age/sex+jockey+trainer tie-break"
    )
    return detail
