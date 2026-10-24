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
    grouped = []
    for ticket in blended["recommendedBets"]:
        group = next((item for item in grouped if item["kind"] == ticket["kind"]), None)
        if group is None:
            group = {"kind": ticket["kind"], "combos": [], "points": 0,
                     "reason": "発走前の実測検証済み統合確率と実オッズの期待回収率から機械選定"}
            grouped.append(group)
        group["combos"].append(ticket["combo"])
        group["points"] += 1
    win, podium = blended["win"], blended["top3"]
    status = "ready" if marks else "unavailable"
    texts = [
        "みねた氏の公開展開手法による観測項目を主体に、複数予想家と独立AIの"
        "同一過去レースでの実測的中率・回収率による重み付けで統合。",
        "中央と地方は別々に検証。",
        "先行候補は" + "、".join(str(n) + "番" for n in mineta["forwardIntentCandidates"]) + "。",
        "初角までの公式距離は" +
        (str(mineta["firstCornerMetersOfficial"]) + "m。" if mineta["firstCornerMetersOfficial"] is not None
         else "未取得。"),
        "◎は" + str(order[0]) + "番。人による印の変更は行わない。",
        "確率はモデル予測であり、個別レースの的中保証ではない。",
        ("実オッズと3着までの各着順確率が揃った買い目のみ掲載。"
         if grouped else "実オッズまたは3着までの着順確率・期待値の条件未達により買い目見送り。"),
    ]
    stages = {
        "ability": {"status": "independently-evaluated-opinions",
                    "value": {k: v.get("modelVersion") for k, v in methods.items()}},
        "runningStyle": {"status": "observed-preoff-positions",
                         "value": {str(e["horseNumber"]): e["pastEarlyTop3Share"]
                                   for e in mineta["horses"]}},
        "pace": {"status": "mineta-public-observed-context", "value": mineta,
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
        "paceEvidence": mineta, "humanOverrideAllowed": False,
    }
