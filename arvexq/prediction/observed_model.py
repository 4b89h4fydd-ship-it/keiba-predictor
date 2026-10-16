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


_JRA_TRACKS = frozenset(("札幌", "函館", "福島", "新潟", "東京", "中山",
                         "中京", "京都", "阪神", "小倉"))


def _run_circuit(run):
    explicit = str(run.get("circuit") or run.get("organization") or "").strip().lower()
    if explicit in ("中央", "jra", "central"):
        return "JRA"
    if explicit in ("地方", "nar", "local"):
        return "NAR"
    track = str(run.get("track") or "").strip()
    if track in _JRA_TRACKS:
        return "JRA"
    # Do not infer from an arbitrary missing or unknown track.
    if track in ("門別", "帯広", "盛岡", "水沢", "浦和", "船橋", "大井", "川崎",
                 "金沢", "笠松", "名古屋", "園田", "姫路", "高知", "佐賀"):
        return "NAR"
    return None


def _history_rates(horse, race):
    """Split observed histories by circuit; never equate JRA and NAR classes.

    Only known same-circuit performances influence the adjusted score.
    Cross-circuit starts are retained as documented transfer evidence but not
    assigned an invented equivalent-class multiplier.
    """
    runs = observed_runs(_course_history(horse, race), race, limit=None)
    target = "JRA" if model_version(race) == JRA_MODEL_VERSION else "NAR"
    same = [r for r in runs if _run_circuit(r) == target]
    other = [r for r in runs if _run_circuit(r) not in (target, None)]
    unknown = [r for r in runs if _run_circuit(r) is None]
    # Only independently observed, normalized opponent-strength evidence can
    # support a cross-circuit class adjustment. Otherwise keep it unknown.
    def _level(run):
        try:
            value = float(run.get("opponentLevel"))
            return value if 0.0 <= value <= 1.0 else None
        except (TypeError, ValueError):
            return None

    target_level = _level(race)
    comparable_cross = [r for r in other if _level(r) is not None and target_level is not None]
    # Relative form within observed opponent strength, not a hardcoded JRA bonus.
    # Use a very conservative reliability shrinkage; the weight must later
    # be calibrated against sealed pre-off races before production adoption.
    transfer_quality = [
        ((r["fieldSize"] - r["finish"]) / (r["fieldSize"] - 1)) * (0.5 + 0.5 * _level(r))
        for r in comparable_cross if r["fieldSize"] > 1
    ]
    transfer_signal = (sum(transfer_quality) / len(transfer_quality) - 0.5) * (
        len(transfer_quality) / (len(transfer_quality) + 8.0)
    ) if transfer_quality else 0.0
    n = len(same)
    wins = sum(int(r["finish"]) == 1 for r in same)
    top2 = sum(int(r["finish"]) <= 2 for r in same)
    top3 = sum(int(r["finish"]) <= 3 for r in same)
    shrink = n / (n + 8.0) if n else 0.0
    latest = _run_circuit(runs[0]) if runs else None
    return {
        "starts": n, "recordedStarts": len(runs),
        "sameCircuitStarts": n, "otherCircuitStarts": len(other),
        "unknownCircuitStarts": len(unknown),
        "latestRecordedCircuit": latest,
        "targetCircuit": target,
        "transferEvidence": bool(other),
        "transferClassEvidenceStarts": len(transfer_quality),
        "targetOpponentLevel": target_level,
        "transferClassSignal": transfer_signal,
        "transferClassStatus": "observed-opponent-proxy-uncalibrated" if transfer_quality else "unknown-no-comparable-opponent-evidence",
        "winRate": wins / n if n else None,
        "top2Rate": top2 / n if n else None,
        "top3Rate": top3 / n if n else None,
        "winEvidence": shrink * (wins / n - 0.12) if n else 0.0,
        "top2Evidence": shrink * (top2 / n - 0.25) if n else 0.0,
        "top3Evidence": shrink * (top3 / n - 0.38) if n else 0.0,
        "comparability": "same-circuit-only; cross-circuit-opponent-proxy-unverified",
    }


def _ordered_top3_probabilities(rows):
    """Coherent Plackett-Luce estimates. Not empirically calibrated."""
    import math
    if len(rows) < 3:
        return {}
    peak = max(row["score"] for row in rows)
    weights = [math.exp(max(-40.0, (row["score"] - peak) / 0.15)) for row in rows]
    total = sum(weights)
    out = {int(row["horse"]["horseNumber"]): [0.0, 0.0, 0.0] for row in rows}
    for i, wi in enumerate(weights):
        p1 = wi / total
        ni = int(rows[i]["horse"]["horseNumber"])
        out[ni][0] += p1
        for j, wj in enumerate(weights):
            if j == i:
                continue
            second = p1 * wj / (total - wi)
            nj = int(rows[j]["horse"]["horseNumber"])
            out[nj][1] += second
            for k, wk in enumerate(weights):
                if k == i or k == j:
                    continue
                third = second * wk / (total - wi - wj)
                nk = int(rows[k]["horse"]["horseNumber"])
                out[nk][2] += third
    return {number: {
        "winProbability": round(v[0], 8),
        "top2Probability": round(v[0] + v[1], 8),
        "top3Probability": round(sum(v), 8),
        "probabilityStatus": "uncalibrated-model-estimate",
    } for number, v in out.items()}


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
        rates = _history_rates(h, race)
        base = .60 * position + .40 * margin["score"]
        score = (base + .12 * rates["winEvidence"] + .06 * rates["top2Evidence"]
                 + .04 * rates["top3Evidence"] + .04 * rates["transferClassSignal"])
        rows.append(dict(horse=h, score=score, factors={"mineta": position, "margin": margin["score"]},
                         marginCoverage=margin["coverage"], sample=len(runs), historicalRates=rates, modelVersion=model_version(race)))
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
    probabilities = _ordered_top3_probabilities(ranked) if full else {}
    axis_candidates = []
    for row in ranked:
        history = observed_runs(_course_history(row["horse"], detail), detail, limit=5)
        if version == JRA_MODEL_VERSION:
            history = [run for run in history if _verified_jra_proof(run)]
        valid = []
        suitability = []
        for run in history:
            try:
                finish = int(run.get("finish") or 0)
                field = int(run.get("fieldSize") or 0)
            except (TypeError, ValueError):
                continue
            if 1 <= finish <= field and field >= 2:
                valid.append(finish)
                try:
                    distance_match = abs(float(run.get("distance")) - float(detail.get("distance"))) <= 150
                except (TypeError, ValueError):
                    distance_match = False
                if distance_match and run.get("surface") == detail.get("surface"):
                    suitability.append(finish <= 3)
        if len(valid) >= 3:
            podium = sum(finish <= 3 for finish in valid)
            ratio = podium / len(valid)
            # Three observed runs minimum; shrink the place rate and use
            # observed same-surface/distance results as a secondary signal.
            stable = (podium + 1) / (len(valid) + 2)
            comparable = sum(suitability) / len(suitability) if suitability else stable
            axis_score = (.45 * stable + .15 * comparable + .15 * row["score"]
                          + .15 * (.38 + row.get("historicalRates", {}).get("top3Evidence", 0.0))
                          + .10 * probabilities.get(int(row["horse"]["horseNumber"]), {}).get("top3Probability", 0.0))
            axis_candidates.append((axis_score, row["score"], -int(row["horse"]["horseNumber"]), row, ratio))
    axis_row = max(axis_candidates, default=None)
    axis_no = int(axis_row[3]["horse"]["horseNumber"]) if axis_row and full else 0
    axis_ratio = axis_row[4] if axis_row else None
    old_fields = ("multiHead", "strengthHeadRank", "winHeadRank", "upsideHeadRank",
                  "upsideCandidate", "dangerPopular", "podiumAxisScore",
                  "factorEvidence", "coreAbilityRank", "coreAbilityScore", "primaryPillars")
    for h in horses:
        e = h.setdefault("integratedEvaluation", {})
        for k in old_fields:
            e.pop(k, None)
        e.update(mark="", markSource=version, markEngineVersion=version,
                 honmeiRole="", honmeiGrade="", honmeiEligible=False,
                 podiumAxisEligible=False)
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
                 independentAxisCandidate=bool(axis_no and int(h["horseNumber"]) == axis_no),
                 honmeiGrade=grade if i == 0 else "",
                 honmeiEligible=bool(i == 0 and grade == "A"),
                 podiumAxisEligible=bool(axis_no and int(h["horseNumber"]) == axis_no),
                 score=round(row["score"] * 100, 2), samples=row["sample"],
                 historicalRates=row.get("historicalRates", _history_rates(h, detail)),
                 modelProbabilities=probabilities.get(int(h["horseNumber"]), {}),
                 neutralPrior=False, confidence="実測",
                 narModelEvidence={"mineta": row["factors"]["mineta"],
                                   "margin": row["factors"]["margin"],
                                   "marginCoverage": row["marginCoverage"],
                                   "sample": row["sample"], "historicalRates": row["historicalRates"]})
        detail["factorRanking"].append({"horseNumber": int(h["horseNumber"]),
                                        "name": h.get("name") or "", "rank": row["rank"],
                                        "dominanceScore": round(row["score"] * 100, 2),
                                        "factors": row["factors"], "modelVersion": version})
    detail["predictionStatus"] = ("ready" if full and len(ranked) >= 2 else
                                  "partial-observed-inputs" if ranked else
                                  "insufficient-observed-inputs")
    detail["markEngineVersion"] = version
    detail["predictionModelVersion"] = version
    detail["markMethod"] = ("中央" if version == JRA_MODEL_VERSION else "地方") + "専用：みねた位置取り代理指標60%＋実測着差40%＋過去勝率・連対率・3着内率（出走数補正）"
    detail["probabilityModelStatus"] = "uncalibrated-model-estimate"
    detail["observedModelCoverage"] = {"horses": len(active), "fullyObserved": len(ranked),
                                     "allObserved": full}
    detail["honmeiDecision"] = {
        "version": version, "eligible": grade == "A",
        "horseNumber": int(top["horse"]["horseNumber"]) if top else 0,
        "displayHonmei": bool(top), "confidenceGrade": grade if top else "",
        "role": "win", "axisHorseNumber": axis_no,
        "axisPlaceRatio": round(axis_ratio, 6) if axis_ratio is not None else None,
        "axisStabilityScore": round(axis_row[0], 6) if axis_row else None,
        "fixedAxisAllowed": bool(axis_no and grade == "A"),
        "axisScore": round(axis_row[0], 6) if axis_row else None,
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
