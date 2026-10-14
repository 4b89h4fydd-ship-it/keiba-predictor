from __future__ import annotations

from typing import Any
from arvexq.prediction.factor_model import MODEL_VERSION, PRIMARY_PILLARS, rank_factor_model
from arvexq.prediction.career_readiness import attach_career_readiness

MARK_ENGINE_VERSION = "arvexq-true-run-pure-sectional-marks-v4-individual-evidence"
CORE_MARKS = ("◎", "○", "▲", "△")
LOWER_MARKS = ("☆",)

def optional_star_candidate(
    ranked: list[dict[str, Any]], race: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Select one evidence-backed pace upside runner outside the four core marks.

    Only recorded pre-off pace fit and observed finishing/run style are used.
    Different cutoffs reflect JRA vs local racing, without awarding a star
    purely for an adequate overall factor score.
    """
    if len(ranked) < 5:
        return None
    race = race or {}
    circuit = str(race.get("circuit") or "")
    local = circuit in ("地方", "NAR", "local")
    score_floor = .55 if local else .60
    gap_ceiling = .19 if local else .15
    pace_floor = .66 if local else .72
    fourth_score = float(ranked[3]["score"])
    eligible = []
    for row in ranked[4:]:
        horse = row["horse"]
        factors = row.get("factors") or {}
        if row.get("primaryPillarCoverage", 0) < 2:
            continue
        score = float(row["score"])
        if score < score_floor or fourth_score - score > gap_ceiling:
            continue
        # Pace-fit must be observed in the race data, not manufactured.
        fit = horse.get("paceFitScore")
        if fit is None:
            fit = horse.get("paceFit")
        if fit is None:
            fit = horse.get("展開適性")
        if isinstance(fit, dict):
            fit = fit.get("score")
        try:
            pace_fit = float(fit)
        except (ValueError, TypeError):
            continue
        if pace_fit > 1:
            pace_fit /= 100
        if not (0 <= pace_fit <= 1) or pace_fit < pace_floor:
            continue
        # Upside also needs independent recent-race sectional OR pace evidence.
        sectional = factors.get("sectional")
        true_run = factors.get("trueRun")
        if not (
            sectional is not None and float(sectional) >= (.63 if local else .68)
            or true_run is not None and float(true_run) >= (.68 if local else .72)
        ):
            continue
        eligible.append((pace_fit, score, horse))
    if not eligible:
        return None
    eligible.sort(key=lambda value: (-value[0], -value[1],
                                    int(value[2].get("horseNumber") or 999)))
    return eligible[0][2]


def sufficiently_observed_partial_career(
    detail: dict[str, Any], readiness: dict[str, Any]
) -> bool:
    """Allow a clearly labelled provisional pre-off forecast from real recent runs.

    A full-career verification is NOT needed by this three-factor model, which
    uses the last five dated starts. Each runner whose lifetime-data audit is
    incomplete must nevertheless have at least three distinct valid pre-off
    races. Reject contradictory reported totals and unknown runner identities.
    Never reclassify any lifetime history as fully verified.
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
    blocked = readiness.get("blockedHorses") or []
    if total < 5 or total != int(readiness.get("activeHorses") or 0) or not blocked:
        return False
    by_no = {int(h["horseNumber"]): h for h in horses}
    disallowed = {"identity-mismatch", "future-race-evidence",
                  "reported-starts-contradiction", "race-identity-mismatch"}
    for entry in blocked:
        horse = by_no.get(int(entry.get("horseNumber") or 0))
        if not horse or not str(horse.get("name") or "").strip():
            return False
        if str(entry.get("reason") or "") in disallowed:
            return False
        try:
            runs = observed_runs(horse, detail, limit=5)
        except (ValueError, TypeError, KeyError):
            return False
        if len(runs) < 3:
            return False
        observed = int(entry.get("observedRuns") or 0)
        reported = entry.get("reportedStarts")
        if reported is not None:
            try:
                if int(reported) < observed or int(reported) < len(runs):
                    return False
            except (TypeError, ValueError):
                return False
    return True


def apply_core_marks(detail: dict[str, Any]) -> dict[str, Any]:
    """One marks authority; old four-pillar and podium-axis paths deleted."""
    if not isinstance(detail, dict):
        return detail
    attach_career_readiness(detail)
    horses = [h for h in (detail.get("horses") or []) if isinstance(h, dict)]
    readiness = detail.get("careerReadiness") or {}
    full = readiness.get("ready") is True
    # Incomplete lifetime acquisition is not proof that observed pre-off runs
    # are unusable. Qualify each runner independently instead of blanking the
    # whole race because one runner's lifetime record is unfinished.
    from arvexq.prediction.past_performance import observed_runs
    from arvexq.core.runner_status import is_inactive_runner
    disallowed = {"identity-mismatch", "future-race-evidence",
                  "reported-starts-contradiction", "race-identity-mismatch"}
    blocked = {int(x.get("horseNumber") or 0): x for x in readiness.get("blockedHorses", [])
               if isinstance(x, dict)}
    usable = []
    for horse in horses:
        if is_inactive_runner(horse) or int(horse.get("horseNumber") or 0) < 1:
            continue
        item = blocked.get(int(horse["horseNumber"]), {})
        if item.get("reason") in disallowed:
            continue
        try:
            runs = observed_runs(horse, detail, limit=5)
        except (TypeError, ValueError, KeyError):
            continue
        # Debutants have no earlier race evidence and must not receive
        # synthetic rankings; require two real, dated prior performances.
        if len(runs) >= 3:
            usable.append(horse)
    limited = not full
    # A partial field is sealable only if every active runner meets the same
    # minimum observed-runs gate. Do not silently exclude a poorly observed
    # entrant and seal a misleading complete-field forecast.
    partial_safe = full or sufficiently_observed_partial_career(detail, readiness)
    detail["predictionStatus"] = ("ready" if full else
                                  "partial-career-evidence" if partial_safe else
                                  "waiting-for-full-career")
    readiness["predictionEligible"] = len(usable) >= 2 and partial_safe
    if limited:
        readiness["predictionEvidencePolicy"] = "three-dated-preoff-starts-per-unverified-horse-v3"
    ranked = rank_factor_model(usable, detail) if len(usable) >= 2 and partial_safe else []
    for horse in horses:
        e = horse.setdefault("integratedEvaluation", {})
        e["mark"] = ""
        e["markEngineVersion"] = MARK_ENGINE_VERSION
        e["markSource"] = "true-run-pure-sectional-45-35-20"
        for old in ("multiHead", "strengthHeadRank", "winHeadRank", "upsideHeadRank",
                    "upsideCandidate", "dangerPopular", "podiumAxisScore"):
            e.pop(old, None)
    detail.pop("multiHeadSummary", None)
    if not ranked:
        if detail["predictionStatus"] != "waiting-for-full-career":
            detail["predictionStatus"] = "insufficient-three-factor-evidence"
        detail.pop("factorRanking", None)
        detail.pop("honmeiDecision", None)
        return detail
    detail["factorRanking"] = []
    leader = ranked[0]
    gap = leader["score"] - ranked[1]["score"] if len(ranked) > 1 else 0.
    complete = leader["primaryPillarCoverage"] == 3
    grade = ("A" if complete and leader["score"] >= .80 and gap >= .04 and leader["sample"] >= 3
             else "B" if leader["primaryPillarCoverage"] >= 2 and leader["score"] >= .65
             else "C")
    axis = leader["horse"]
    axis_no = int(axis.get("horseNumber") or 0)
    detail["honmeiDecision"] = {
        "version": MARK_ENGINE_VERSION, "eligible": grade == "A",
        "horseNumber": axis_no, "displayHonmei": True, "confidenceGrade": grade,
        "role": "win", "fixedAxisAllowed": grade == "A", "axisScore": round(leader["score"], 6),
        "axisMargin": round(gap, 6), "axisMeaning": "relative-three-factor-score-not-probability",
        "reason": "three-factor-confidence" if grade == "A" else "relative-honmei-not-fixed",
        "axisCandidates": [
            {"horseNumber": int(z["horse"].get("horseNumber") or 0),
             "score": round(z["score"], 6), "coverage": z["primaryPillarCoverage"]}
            for z in ranked[:5]
        ]
    }
    for row in ranked:
        h = row["horse"]
        e = h.setdefault("integratedEvaluation", {})
        evidence = {
            "rank": row["rank"], "dominanceScore": row["dominanceScore"],
            "scoreMeaning": "TRUE RUN 45 + PURE 35 + SECTIONAL 20, not probability",
            "pillarScores": row["pillarScores"], "pillarRanks": row["pillarRanks"],
            "evidenceCounts": row["evidenceCounts"],
            "evidenceFamilyCounts": row["evidenceFamilyCounts"],
            "primaryPillarCoverage": row["primaryPillarCoverage"],
            "rawMetrics": row["raw"], "sample": row["sample"],
            "modelVersion": MODEL_VERSION,
        }
        e["coreAbilityRank"] = row["rank"]
        e["coreAbilityScore"] = row["dominanceScore"]
        e["primaryPillars"] = list(PRIMARY_PILLARS)
        e["factorEvidence"] = evidence
        e["pastPerformance"] = row["pastPerformance"]
        e["careerProfile"] = row["careerProfile"]
        e["honmeiEligible"] = bool(grade == "A" and h is axis)
        e["honmeiRole"] = "win" if h is axis else ""
        e["honmeiGrade"] = grade if h is axis else ""
        e["honmeiGateVersion"] = MARK_ENGINE_VERSION
        h["abilityEvidence"] = evidence
        detail["factorRanking"].append({
            "horseNumber": int(h.get("horseNumber") or 0),
            "name": h.get("name") or "", **evidence,
        })
    # One ranking owns the four mandatory marks; ☆ needs independent evidence.
    for row, mark in zip(ranked, CORE_MARKS):
        row["horse"]["integratedEvaluation"]["mark"] = mark
    star = optional_star_candidate(ranked, detail)
    if star is not None:
        star["integratedEvaluation"]["mark"] = "☆"
    for row in ranked:
        row["horse"]["integratedEvaluation"]["rank"] = row["rank"]
    detail["markEngineVersion"] = MARK_ENGINE_VERSION
    detail["predictionModelVersion"] = MODEL_VERSION
    detail["markMethod"] = "TRUE RUN45%＋PURE35%＋SECTIONAL20%; unified marks and betting"
    return detail
