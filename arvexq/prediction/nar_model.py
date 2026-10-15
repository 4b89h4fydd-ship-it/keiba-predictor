"""Only live NAR prediction authority: observed Mineta-position proxy 60% + margin 40%.

The published 25-race retrospective is not a prospective performance guarantee.
Missing historical margins or first corners are NOT replaced by old-model scores.
JRA never enters this module. Immutable pre-off records are not modified here.
"""
from __future__ import annotations

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.special_marks import allocate_special_marks
from arvexq.research.mineta_field_proxy import score_race as mineta_scores
from arvexq.research.margin_abcde_candidate import score as margin_score

MODEL_VERSION = "arvexq-nar-mineta-margin-60-40-v1"


def _active(h):
    return isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0 and not is_inactive_runner(h)


def rank_nar(horses, race):
    """Rank observed runners; no neutral scores or legacy fallback."""
    horses = [h for h in horses if _active(h)]
    mineta = mineta_scores(horses, race)
    rows = []
    for h in horses:
        number = int(h["horseNumber"])
        position = mineta.get(number)
        margin = margin_score(h, race)
        if position is None or margin is None:
            continue
        runs = observed_runs(h, race, limit=5)
        score = .60 * position + .40 * margin["score"]
        rows.append(dict(horse=h, score=score, factors={"mineta": position, "margin": margin["score"]},
                         marginCoverage=margin["coverage"], sample=len(runs), modelVersion=MODEL_VERSION))
    rows.sort(key=lambda row: (-row["score"], int(row["horse"]["horseNumber"])))
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return rows


def apply_nar_marks(detail):
    """Replace old NAR prediction, marks, and their ranking input in place."""
    if str(detail.get("circuit") or "") not in ("地方", "NAR", "local"):
        raise ValueError("NAR model cannot score a JRA race")
    horses = detail.get("horses") or []
    active = [h for h in horses if _active(h)]
    ranked = rank_nar(active, detail)
    full = bool(active) and len(ranked) == len(active)
    gap = ranked[0]["score"] - ranked[1]["score"] if len(ranked) > 1 else 0.
    top = ranked[0] if ranked else None
    grade = ("A" if full and len(ranked) >= 5 and gap >= .055 and top["sample"] >= 3 else
             "B" if full and len(ranked) >= 2 else "C")
    old_fields = ("multiHead", "strengthHeadRank", "winHeadRank", "upsideHeadRank",
                  "upsideCandidate", "dangerPopular", "podiumAxisScore",
                  "factorEvidence", "coreAbilityRank", "coreAbilityScore", "primaryPillars")
    for h in horses:
        e = h.setdefault("integratedEvaluation", {})
        for k in old_fields:
            e.pop(k, None)
        e.update(mark="", markSource=MODEL_VERSION, markEngineVersion=MODEL_VERSION,
                 honmeiRole="", honmeiGrade="", honmeiEligible=False)
    special = allocate_special_marks(ranked, detail)
    detail["factorRanking"] = []
    for i, row in enumerate(ranked):
        h = row["horse"]
        e = h["integratedEvaluation"]
        observed = special.get(int(h["horseNumber"]), {})
        e.update(mark=observed.get("mark", ""),
                 specialMarkEvidence={k: v for k, v in observed.items() if k != "mark"},
                 coreAbilityRank=i + 1, coreAbilityScore=round(row["score"] * 100, 2),
                 honmeiRole="win" if i == 0 else "",
                 honmeiGrade=grade if i == 0 else "",
                 honmeiEligible=bool(i == 0 and grade == "A"),
                 narModelEvidence={"mineta": row["factors"]["mineta"],
                                   "margin": row["factors"]["margin"],
                                   "marginCoverage": row["marginCoverage"],
                                   "sample": row["sample"]})
        detail["factorRanking"].append({"horseNumber": int(h["horseNumber"]),
                                        "name": h.get("name") or "", "rank": row["rank"],
                                        "dominanceScore": round(row["score"] * 100, 2),
                                        "factors": row["factors"], "modelVersion": MODEL_VERSION})
    detail["predictionStatus"] = ("ready" if full and len(ranked) >= 2 else
                                  "partial-nar-observed-inputs" if ranked else
                                  "insufficient-nar-observed-inputs")
    detail["markEngineVersion"] = MODEL_VERSION
    detail["predictionModelVersion"] = MODEL_VERSION
    detail["markMethod"] = "地方専用：みねた位置取り代理指標60%＋公式過去走着差40%"
    detail["narObservedCoverage"] = {"horses": len(active), "fullyObserved": len(ranked),
                                     "allObserved": full}
    detail["honmeiDecision"] = {
        "version": MODEL_VERSION, "eligible": grade == "A",
        "horseNumber": int(top["horse"]["horseNumber"]) if top else 0,
        "displayHonmei": bool(top), "confidenceGrade": grade if top else "",
        "role": "win", "fixedAxisAllowed": grade == "A",
        "axisScore": round(top["score"], 6) if top else None,
        "axisMargin": round(gap, 6), "axisMeaning": "uncalibrated-relative-model-score",
        "reason": "observed-nar-mineta-margin-60-40" if full else "incomplete-nar-observations"}
    detail.pop("multiHeadSummary", None)
    return detail
