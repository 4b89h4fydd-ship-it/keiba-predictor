"""Existing public pre-off forecast entry point: empirical Mineta/expert/AI fusion.

Stage64 does NOT execute. There is no synthetic fallback if independently
recorded pre-off forecasts, earlier evaluation weights or genuine odds are
missing. Frozen historical originals are handled by publication.py.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

VERSION = "arvexq-empirical-fusion-v1"

JST = ZoneInfo("Asia/Tokyo")


def _has_result_evidence(value):
    """Allow only empty, explicitly pending result placeholders before the off."""
    if not value:
        return False
    if not isinstance(value, dict):
        return True
    if set(value) - {"status", "finishers", "payouts"}:
        return True
    if value.get("finishers") or value.get("payouts"):
        return True
    return str(value.get("status") or "").strip() not in {"", "未確定", "未取得", "発走前", "未発走"}


def _preoff(facts, now):
    if not isinstance(facts, dict) or not isinstance(facts.get("date"), str):
        return False
    if _has_result_evidence(facts.get("result")) or str(facts.get("raceStatus") or "") in {"速報", "確定", "終了"}:
        return False
    start = facts.get("scheduledStartTime") or facts.get("startTime")
    if not isinstance(start, str) or len(start) < 5:
        return False
    try:
        scheduled = datetime.fromisoformat(f"{facts['date']}T{start[:5]}:00").replace(tzinfo=JST)
        current = now or datetime.now(JST)
        if current.tzinfo is None:
            current = current.replace(tzinfo=JST)
        else:
            current = current.astimezone(JST)
        return facts["date"] >= "2026-10-23" and current < scheduled
    except (TypeError, ValueError):
        return False





def build_prediction(facts, now=None):
    """Return the six existing product stages from empirically fitted inputs.

    The ONLY input path is the pre-existing race-detail payload. Its
    `fusionInputs` must be prepared from genuine, independently dated,
    same-roster method outputs on that path; never synthesize votes here.
    """
    # Import within the now-initialized production entry point: the legacy
    # prediction package imports forecast.engine for its compatibility adapter.
    from arvexq.prediction.empirical_fusion import blend
    from arvexq.prediction.mineta_public_pace import public_pace_factors
    from arvexq.prediction.past_performance import analyze_past_performance
    from arvexq.prediction.career_profile import profile_career
    if not _preoff(facts, now):
        return None
    if facts.get("track") in ("帯広", "帯広ば") or facts.get("surface") in ("ばんえい", "障害"):
        return None
    origin = {"jra": "中央", "nar": "地方", "中央": "中央", "地方": "地方"}
    owner = origin.get(facts.get("circuit"))
    if owner is None or not isinstance(facts.get("horses"), list):
        return None
    supplied = facts.get("fusionInputs")
    if not isinstance(supplied, dict):
        return None
    methods, fit = supplied.get("opinions"), supplied.get("calibration")
    if not isinstance(methods, dict) or not isinstance(fit, dict):
        return None
    race = dict(facts, circuit=owner)
    try:
        mineta = public_pace_factors(race)
        blended = blend(race, methods, fit, quoted_odds=supplied.get("odds"))
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    # The computed opinion clock is part of the original pre-off evidence.
    # A forecast without a single consistent real capture cannot be sealed.
    capture_times={o.get("capturedAt") for o in methods.values()}
    if len(capture_times)!=1 or not next(iter(capture_times)):
        return None
    captured_at=next(iter(capture_times))
    if supplied.get("capturedAt") is not None and supplied["capturedAt"]!=captured_at:
        return None
    marks = blended["predictionMarks"]
    order = [m["horseNumber"] for m in marks]
    if len(marks) != 5 or len(set(order)) != 5 or any(
            m.get("mark") != ("◎", "○", "▲", "△", "☆")[i]
            for i, m in enumerate(marks)):
        return None
    grouped = []
    for ticket in blended["recommendedBets"]:
        combo = ticket.get("combo") if isinstance(ticket, dict) else None
        if not isinstance(combo, list) or not combo or not set(combo).issubset(set(order)):
            # A ticket that names an unmarked runner is not the same product
            # as this forecast. Fail closed instead of displaying mixed
            # sources.
            return None
        group = next((item for item in grouped if item["kind"] == ticket["kind"]), None)
        if group is None:
            group = {"kind": ticket["kind"], "combos": [], "points": 0,
                     "reason": "発走前の実測検証済み統合確率と実オッズの期待回収率から機械選定"}
            grouped.append(group)
        group["combos"].append(ticket["combo"])
        group["points"] += 1
    win, podium = blended["win"], blended["top3"]
    status = "ready" if marks else "unavailable"
    pace = dict(mineta)
    verified_video = [
        row for horse in race.get("horses") or [] if isinstance(horse, dict)
        for row in (horse.get("visionResearchHistory") or [])
        if isinstance(row, dict)
        and row.get("researchOnly") is True
        and row.get("identitySource") == "externally-reviewed"
        and type(row.get("trackingCoverage")) in (int, float)
        and row["trackingCoverage"] >= .8
    ]
    pace["verifiedHistoricalVideoRuns"] = len(verified_video)
    pace["videoAppliedToFusion"] = bool(verified_video)
    # The existing pace stage carries the four-phase historical baseline.
    # It is descriptive only; never silently feed uncalibrated ranks into
    # the fused win probabilities, marks, or ticket decisions.
    pace["fourPhaseHistoricalBaseline"] = {
        str(entry["horseNumber"]): entry["phaseProjection"]
        for entry in mineta["horses"]
    }
    pace["fourPhaseBaselineValidated"] = False
    pace["markOrder"] = order
    pace["markLabels"] = {str(m["horseNumber"]): m["mark"] for m in marks}
    pace["ticketHorses"] = sorted({no for ticket in blended["recommendedBets"]
                                    for no in ticket["combo"]})
    texts = [
        "みねた氏の公開展開手法による観測項目を主体に、複数予想家と独立AIの"
        "同一過去レースでの実測的中率・回収率による重み付けで統合。",
        "中央と地方は別々に検証。",
        ("外部レビュー済み・過去レース一致の映像計測" + str(len(verified_video))
         + "走を融合特徴量へ反映。" if verified_video else
         "条件を満たす映像計測はなく、映像値は予想へ反映していない。"),
        "先行候補は" + "、".join(str(n) + "番" for n in mineta["forwardIntentCandidates"]) + "。",
        "初角までの公式距離は" +
        (str(mineta["firstCornerMetersOfficial"]) + "m。" if mineta["firstCornerMetersOfficial"] is not None
         else "未取得。"),
        "印は融合確率順位から機械決定し、◎は" + str(order[0]) + "番。"
        "展開・確率・印・買い目はこの同一融合結果から作成し、人による変更は行わない。",
        "確率はモデル予測であり、個別レースの的中保証ではない。",
        ("実オッズと3着までの各着順確率が揃った買い目のみ掲載。"
         if grouped else "実オッズまたは3着までの着順確率・期待値の条件未達により買い目見送り。"),
    ]
    # Ability stage 1: reuse the existing race-dated five-run and full-career
    # evidence. Keep these factual observations separate from calibrated
    # probabilities, marks and all future-stage predictions.
    ability_observations = {}
    for horse in race["horses"]:
        if not isinstance(horse, dict) or type(horse.get("horseNumber")) is not int:
            continue
        no = horse["horseNumber"]
        if no not in win:
            continue
        recent = analyze_past_performance(horse, race)
        career = profile_career(horse, race)
        ability_observations[str(no)] = {
            "recentRuns": recent["datedRuns"],
            "recentTop3Rate": recent["top3Rate"],
            "recentFormQuality": recent["recentFormQuality"],
            "opponentLevelMean": recent["opponentLevelMean"],
            "opponentEvidenceRuns": recent["opponentLevelObservedRuns"],
            "marginMean": recent["marginMean"],
            "marginEvidenceRuns": recent["marginObservedRuns"],
            "comparableRuns": career["comparableRuns"],
            "comparableQuality": career["comparableQuality"],
            "sameTrackQuality": career["sameTrackQuality"],
            "sameDistanceQuality": career["sameDistanceQuality"],
            "sameSurfaceQuality": career["sameSurfaceQuality"],
            "sameGoingQuality": career["sameGoingQuality"],
            "fullCareerRuns": career["datedRuns"],
            "historyCoverage": career["coverageStatus"],
            "status": "observed-only" if career["datedRuns"] else "missing-dated-career-history",
        }
    stages = {
        "ability": {"status": "observed-ability-inputs-not-calibrated",
                    "value": {k: v.get("modelVersion") for k, v in methods.items()},
                    "horseEvidence": ability_observations,
                    "probabilityCalibrationVerified": False},
        "runningStyle": {"status": "observed-preoff-positions",
                         "value": {str(e["horseNumber"]): e["pastEarlyTop3Share"]
                                   for e in mineta["horses"]}},
        "pace": {"status": "mineta-public-observed-context", "value": pace,
                 "scenarioWeightsVerified": False},
        "probability": {"status": "empirical-multi-model-weighted", "value":
                        {"win": win, "top3": podium},
                        "calibrationVerified": False},
        "marks": {"status": "mechanical-no-override",
                  "value": {"orderedWinCandidates": order,
                            "orderedAxisCandidates": sorted(podium, key=lambda n:(-podium[n], n)),
                            "productMarks": marks}},
        "tickets": {"status": blended["betStatus"], "value": grouped},
    }
    return {
        "raceId": race["id"], "date": race["date"], "circuit": owner,
        "capturedAt": captured_at,
        "methodologyStatus": "public-method-replicas-and-two-independent-fitted-AI-models",
        "actualForecasterPublishedPicks": False,
        "calibrationMethod": fit.get("calibrationMethod", "actual-frozen-preoff-evaluations"),
        "modelVersion": VERSION, "predictionStatus": status,
        "productionEligible": status == "ready", "stages": stages,
        "predictionMarks": marks, "recommendedBets": grouped,
        "methodWeights": blended["methodWeights"], "methodEvidence": blended["methodEvidence"],
        "calibrationRaces": blended["calibrationRaces"], "forecastText": "".join(texts),
        "paceEvidence": pace, "humanOverrideAllowed": False,
    }
