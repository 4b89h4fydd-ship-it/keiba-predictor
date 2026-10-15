"""Single pre-off 60% observed positioning + 40% observed margin ranker.

JRA and NAR share one scorer. Differences are explicit: JRA official result
proof, JRA flat versus obstacle history, source surface and course identity.
No retrospective labels, probabilities or synthetic fill-ins enter scoring.
"""
from __future__ import annotations

from arvexq.core.runner_status import is_inactive_runner
from arvexq.prediction.past_performance import observed_runs
from arvexq.prediction.special_marks import allocate_special_marks
from arvexq.research.mineta_field_proxy import score_race as mineta_scores
from arvexq.research.margin_abcde_candidate import score as margin_score

NAR_MODEL_VERSION = "arvexq-nar-mineta-margin-60-40-v1"
JRA_MODEL_VERSION = "arvexq-jra-mineta-margin-60-40-v1"
MODEL_VERSION = NAR_MODEL_VERSION


def model_version(race):
    return JRA_MODEL_VERSION if str(race.get("circuit") or "") in ("中央", "JRA", "central") else NAR_MODEL_VERSION


def _is_obstacle(run):
    import re
    return bool(re.search(r"障害|ジャンプ|\\bJS\\b|J[・･.]?G", str(run.get("surface") or "") + str(run.get("title") or "")))


def _course_history(horse, race):
    """JRA flat/jump are not comparable; avoid mixing unrelated starts."""
    if model_version(race) != JRA_MODEL_VERSION:
        return horse
    jump = _is_obstacle(race) or str(race.get("analysisMode") or "") == "障害"
    out = dict(horse)
    for key in ("recentRaces", "allPastRuns", "pastRaces", "history", "runs"):
        if isinstance(horse.get(key), list):
            out[key] = [x for x in horse[key] if isinstance(x, dict) and _is_obstacle(x) == jump]
    return out


def _verified_jra_proof(run):
    """JRA margins must be tied to observed official results, not an estimate."""
    v = run.get("marginSeconds")
    if v is None or v == "":
        v = run.get("timeBehindWinner")
    if v is None or v == "":
        return False
    try:
        import math
        if not math.isfinite(float(v)):
            return False
    except (ValueError, TypeError):
        return False
    proof = run.get("marginEvidence")
    source = str(run.get("marginEvidenceSource") or "").lower()
    return isinstance(proof, dict) and bool(proof.get("winnerTimeSeconds") is not None and proof.get("horseTimeSeconds") is not None) and ("jra" in source or "official" in source)



def _active(h):
    return isinstance(h, dict) and int(h.get("horseNumber") or 0) > 0 and not is_inactive_runner(h)


def rank_observed(horses, race):
    """Rank observed runners; no neutral scores or legacy fallback."""
    horses = [h for h in horses if _active(h)]
    scoring_horses = [_course_history(h, race) for h in horses]
    mineta = mineta_scores(scoring_horses, race)
    rows = []
    for h, scoring_h in zip(horses, scoring_horses):
        number = int(h["horseNumber"])
        position = mineta.get(number)
        if model_version(race) == JRA_MODEL_VERSION:
            # Only official JRA result evidence qualifies, including genuine 0.0.
            past = observed_runs(scoring_h, race, limit=5)
            valid = [q for q in past if _verified_jra_proof(q)]
            if not valid:
                continue
            scoring_h = dict(scoring_h)
            for key in ("recentRaces", "allPastRuns", "pastRaces", "history", "runs"):
                scoring_h[key] = valid
        margin = margin_score(scoring_h, race)
        if position is None or margin is None:
            continue
        runs = observed_runs(scoring_h, race, limit=5)
        score = .60 * position + .40 * margin["score"]
        rows.append(dict(horse=h, score=score, factors={"mineta": position, "margin": margin["score"]},
                         marginCoverage=margin["coverage"], sample=len(runs), modelVersion=model_version(race)))
    rows.sort(key=lambda row: (-row["score"], int(row["horse"]["horseNumber"])))
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return rows


def apply_observed_marks(detail):
    """Only live marks authority for JRA and NAR; never run a legacy ranker."""
    circuit = str(detail.get("circuit") or "")
    if circuit not in ("地方", "NAR", "local", "中央", "JRA", "central"):
        raise ValueError("unsupported circuit for observed model")
    version = model_version(detail)
    horses = detail.get("horses") or []
    active = [h for h in horses if _active(h)]
    ranked = rank_observed(active, detail)
    full = bool(active) and len(ranked) == len(active)
    gap = ranked[0]["score"] - ranked[1]["score"] if len(ranked) > 1 else 0.
    top = ranked[0] if ranked else None
    grade = ("A" if full and len(ranked) >= 5 and gap >= .055 and top["sample"] >= 3 else
             "B" if full and len(ranked) >= 2 else "C")
    # Axis is independently selected by observed top-three stability.
    # Do not confuse a win ranking with an evidence-backed podium role.
    axis_candidates = []
    for row in ranked:
        history = observed_runs(_course_history(row["horse"], detail), detail, limit=5)
        if version == JRA_MODEL_VERSION:
            history = [run for run in history if _verified_jra_proof(run)]
        valid = []
        for run in history:
            try:
                finish = int(run.get("finish") or 0)
                field = int(run.get("fieldSize") or 0)
            except (TypeError, ValueError):
                continue
            if 1 <= finish <= field and field >= 2:
                valid.append(finish)
        if len(valid) >= 3:
            ratio = sum(finish <= 3 for finish in valid) / len(valid)
            axis_candidates.append((ratio, row["score"], -int(row["horse"]["horseNumber"]), row))
    axis_row = max(axis_candidates, default=None)
    axis_no = int(axis_row[3]["horse"]["horseNumber"]) if axis_row and full else 0
    axis_ratio = axis_row[0] if axis_row else None
    old_fields = ("multiHead", "strengthHeadRank", "winHeadRank", "upsideHeadRank",
                  "upsideCandidate", "dangerPopular", "podiumAxisScore",
                  "factorEvidence", "coreAbilityRank", "coreAbilityScore", "primaryPillars")
    for h in horses:
        e = h.setdefault("integratedEvaluation", {})
        for k in old_fields:
            e.pop(k, None)
        e.update(mark="", markSource=version, markEngineVersion=version,
                 honmeiRole="", honmeiGrade="", honmeiEligible=False)
    # Independent pre-off ☆/注 allocation from PR #181. Keep original
    # ranked horses untouched. Only the JRA evidence view is filtered to
    # the matching flat/jump discipline and verified official history.
    special_rows = []
    for row in ranked:
        evidence_horse = _course_history(row["horse"], detail)
        if version == JRA_MODEL_VERSION:
            evidence_horse = dict(evidence_horse)
            for key in ("recentRaces", "allPastRuns", "pastRaces", "history", "runs"):
                if isinstance(evidence_horse.get(key), list):
                    evidence_horse[key] = [q for q in evidence_horse[key] if _verified_jra_proof(q)]
        special_rows.append({**row, "horse": evidence_horse})
    special = allocate_special_marks(special_rows, detail)
    detail["factorRanking"] = []
    for i, row in enumerate(ranked):
        h = row["horse"]
        e = h["integratedEvaluation"]
        evidence = special.get(int(h["horseNumber"]), {})
        e.update(mark=evidence.get("mark", ""),
                 specialMarkEvidence={k: v for k, v in evidence.items() if k != "mark"},
                 coreAbilityRank=i + 1, coreAbilityScore=round(row["score"] * 100, 2),
                 honmeiRole="win" if i == 0 else ("axis" if int(h["horseNumber"]) == axis_no else ""),
                 honmeiGrade=grade if i == 0 else "",
                 honmeiEligible=bool(i == 0 and grade == "A"),
                 podiumAxisEligible=bool(axis_no and int(h["horseNumber"]) == axis_no),
                 score=round(row["score"] * 100, 2), samples=row["sample"],
                 neutralPrior=False, confidence="実測",
                 narModelEvidence={"mineta": row["factors"]["mineta"],
                                   "margin": row["factors"]["margin"],
                                   "marginCoverage": row["marginCoverage"],
                                   "sample": row["sample"]})
        detail["factorRanking"].append({"horseNumber": int(h["horseNumber"]),
                                        "name": h.get("name") or "", "rank": row["rank"],
                                        "dominanceScore": round(row["score"] * 100, 2),
                                        "factors": row["factors"], "modelVersion": version})
    detail["predictionStatus"] = ("ready" if full and len(ranked) >= 2 else
                                  "partial-observed-inputs" if ranked else
                                  "insufficient-observed-inputs")
    detail["markEngineVersion"] = version
    detail["predictionModelVersion"] = version
    detail["markMethod"] = ("中央" if version == JRA_MODEL_VERSION else "地方") + "専用：みねた位置取り代理指標60%＋実測着差40%"
    detail["observedModelCoverage"] = {"horses": len(active), "fullyObserved": len(ranked),
                                     "allObserved": full}
    detail["honmeiDecision"] = {
        "version": version, "eligible": grade == "A",
        "horseNumber": int(top["horse"]["horseNumber"]) if top else 0,
        "displayHonmei": bool(top), "confidenceGrade": grade if top else "",
        "role": "win", "axisHorseNumber": axis_no,
        "axisPlaceRatio": round(axis_ratio, 6) if axis_ratio is not None else None,
        "fixedAxisAllowed": bool(axis_no and grade == "A"),
        "axisScore": round(top["score"], 6) if top else None,
        "axisMargin": round(gap, 6), "axisMeaning": "uncalibrated-relative-model-score",
        "reason": "observed-mineta-margin-60-40" if full else "incomplete-observations"}
    detail.pop("multiHeadSummary", None)
    return detail


def rank_nar(horses, race):
    if model_version(race) != NAR_MODEL_VERSION:
        raise ValueError("NAR model cannot score a JRA race")
    return rank_observed(horses, race)


def apply_nar_marks(detail):
    if model_version(detail) != NAR_MODEL_VERSION:
        raise ValueError("NAR model cannot score a JRA race")
    return apply_observed_marks(detail)


def rank_jra(horses, race):
    if model_version(race) != JRA_MODEL_VERSION:
        raise ValueError("JRA model cannot score a NAR race")
    return rank_observed(horses, race)
