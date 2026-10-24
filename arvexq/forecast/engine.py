"""Production adapter for the independently separated Stage64 forecast.

Stage64 remains the only calculator.  This module only enforces the public
pre-off boundary and adapts the race-detail payload to its input contract.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.research.stage64.pipeline import predict

VERSION = "arvexq-stage64-product-v1"
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



def _stage64_pace_text(race, prediction):
    """Explain observed early positions without claiming a proven race pace.

    The earlier forward/closer scenario prose treated unsupported corrections
    as if they were tactical evidence. Never label early position as a
    guaranteed lead or invent certainty about a pace battle.
    """
    stages = prediction["stages"]
    evidence = prediction.get("paceEvidence") or {}
    marks = stages["marks"]["value"] or {}
    ranked = marks.get("orderedWinCandidates") or []
    horses = {h["horseNumber"]: h for h in race["horses"]}
    if not ranked:
        return ""

    def name(no):
        return str(horses.get(no, {}).get("name") or f"{no}番")

    profiles = evidence.get("observedPositionProfiles") or {}
    early = [no for no in (evidence.get("earlyPositionObservedOrder") or [])
             if profiles.get(no) in {"前方", "好位"}]
    pieces = [
        "近走の着順から能力を確認し、過去の初角位置は観測された脚質傾向として別に読む。",
        f"現在の◎候補は{name(ranked[0])}。"
        "これは能力評価を基準とした暫定候補であり、的中率を保証しない。",
    ]
    if early:
        pieces.append(
            "初角で前方に位置した観測傾向がある馬は"
            + "、".join(name(no) for no in early[:3]) + "。"
            "前方にいたことと今回逃げることは同義ではない。"
        )
    pieces.append(
        "枠順・発馬・騎手の選択・出走馬同士の競り合いを確認しない限り、"
        "単騎逃げ・ハイペース・差し有利とは断定せず、"
        "根拠のない展開補正で能力上位馬を印から外さない。"
        "複数予想家の根拠融合・AIの独立検証・確率校正は未完了。"
    )
    return "".join(pieces)


def build_prediction(facts, now=None):
    if not _preoff(facts, now):
        return None
    circuit = {"中央": "jra", "地方": "nar"}.get(facts.get("circuit"), facts.get("circuit"))
    if circuit not in {"jra", "nar"}:
        return None
    race = dict(facts)
    race["circuit"] = circuit
    # NAR snapshots may retain the same pre-off history under allPastRuns.
    # The display adapter already uses this alias; pass it to Stage64 without
    # modifying stored rows or changing the model / missing-data policy.
    if circuit == "nar" and isinstance(race.get("horses"), list):
        race["horses"] = [
            {**h, "recentRaces": h["allPastRuns"]}
            if isinstance(h, dict) and not h.get("recentRaces")
            and isinstance(h.get("allPastRuns"), list) and h["allPastRuns"]
            else h
            for h in race["horses"]
        ]
    try:
        result = predict(race, expected_circuit=circuit)
    except (KeyError, TypeError, ValueError):
        return None
    if result.get("blockers") or any(result["stages"][name]["value"] is None
                                     for name in ("ability", "runningStyle", "pace", "probability", "marks", "tickets")):
        return None
    result["stage64ModelVersion"] = result.get("modelVersion")
    result["modelVersion"] = VERSION
    result["productionEligible"] = True
    result["predictionStatus"] = "ready"
    result["forecastText"] = _stage64_pace_text(race, result)
    return result
