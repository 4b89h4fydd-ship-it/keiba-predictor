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

    policy = prediction.get("predictionMethod") or {}
    if policy.get("circuit") == "jra":
        method_text = (
            "中央競馬方式：近走の出走成績を能力判断の基準にし、"
            "コース・距離・相手関係・着差と位置取りを検討する。"
            "地方の全過去走判定は流用しない。"
        )
    elif policy.get("circuit") == "nar":
        coverage = prediction.get("abilityHistoryCoverage") or {}
        full = coverage.get("fullCareerRunners", 0)
        method_text = (
            "地方競馬方式：保存済みの全過去走と直近走が整合する馬"
            + (f"{full}頭" if full else "がないため")
            + ("では長期の能力・脚質・相手との直接対戦を確認する。"
               if full else "確認できる近走だけで判断する。")
            + "中央の近走限定方式は流用しない。"
        )
    else:
        method_text = "予想方法の区分が未確認。"
    profiles = evidence.get("observedPositionProfiles") or {}
    early = [no for no in (evidence.get("earlyPositionObservedOrder") or [])
             if profiles.get(no) in {"前方", "好位"}]
    pieces = [
        method_text,
        "過去の着順から能力を確認し、初角位置は観測された脚質傾向として別に読む。",
        f"現在の◎候補は{name(ranked[0])}。"
        "これは能力評価を基準とした暫定候補であり、的中率を保証しない。",
    ]
    if early:
        pieces.append(
            "初角で前方に位置した観測傾向がある馬は"
            + "、".join(name(no) for no in early[:3]) + "。"
            "前方にいたことと今回逃げることは同義ではない。"
        )
    public = evidence.get("publicPositionTactics") or {}
    if public:
        profiles = public.get("observedProfiles") or {}
        observed_top3 = [
            no for no, item in profiles.items()
            if item.get("top3PositionObserved") is True
        ]
        if observed_top3:
            pieces.append("前走の通過順位で3番手以内を記録した馬は"
                          + "、".join(name(no) for no in observed_top3) + "。")
        extended = public.get("distanceExtensionCandidates") or []
        shortened = public.get("distanceShorteningCandidates") or []
        if extended:
            pieces.append("前走から距離延長は" + "、".join(name(no) for no in extended)
                          + "。前進意識の可能性を確認する対象。")
        if shortened:
            pieces.append("前走から距離短縮は" + "、".join(name(no) for no in shortened)
                          + "。前走の位置取りだけで先行と決めない。")
        adjacency = public.get("adjacentForwardIntentPairs") or []
        if adjacency:
            pieces.append("先行意識の候補が馬番で隣り合う組は"
                          + "、".join(name(a) + "と" + name(b) for a, b in adjacency)
                          + "。実際に競るとは限らない。")
        if public.get("positionUnknown"):
            pieces.append("前走位置取りが未確認の馬は"
                          + "、".join(name(no) for no in public["positionUnknown"])
                          + "。不明を後方脚質として扱わない。")
    course = evidence.get("historicalCourseEvidence") or {}
    # Factual course/distance observations explain where the tentative
    # winner choice may be vulnerable; they do NOT alter marks or probability.
    observed = []
    for no in ranked[:5]:
        record = course.get(no) or {}
        starts = record.get("sameTrackDistanceStarts")
        wins = record.get("sameTrackDistanceWins")
        if isinstance(starts, int) and starts > 0 and isinstance(wins, int) and wins:
            observed.append(f"{name(no)}は同場・同距離で確認できた{starts}走中{wins}勝")
    if observed:
        pieces.append("同場・同距離の過去実績："
                      + "、".join(observed) + "。"
                      "過去の勝利記録は今回の勝利保証ではない。")
    holistic = evidence.get("holisticWinnerEvidence") or {}
    horses_facts = holistic.get("byHorse") or {}
    if ranked:
        first = ranked[0]
        f = horses_facts.get(first) or {}
        relevant = []
        margin = f.get("sameTrackDistanceMarginSeconds")
        margin_samples = f.get("sameTrackDistanceMarginSamples") or 0
        if margin is not None and margin_samples:
            relevant.append("同場同距離の過去着差%s秒（%d走）" %
                            (margin, margin_samples))
        opponent = f.get("opponentLevelMedian")
        if opponent is not None and f.get("opponentLevelSamples"):
            relevant.append("相手水準の観測%d走" % f["opponentLevelSamples"])
        reaction = f.get("individualGateReactionMedian")
        if reaction is not None and f.get("individualGateReactionSamples"):
            relevant.append("個別スタート反応の記録%d走" %
                            f["individualGateReactionSamples"])
        if relevant:
            pieces.append(name(first) + "の過去の根拠は" + "、".join(relevant)
                          + "。条件の異なる時計は直接比較しない。")
    rematch = (prediction.get("winnerEvidenceComparison") or {}).get(
        "proposedHeadToHeadResearchChallenger")
    if rematch:
        count = rematch["sharedPastRacesWon"]
        applied = (prediction.get("winnerEvidenceComparison") or {}).get(
            "appliedToWinProbabilityAndMarks") is True
        pieces.append("過去の直接対戦では" + name(rematch["horseNumber"])
                      + "が" + name(rematch["otherHorseNumber"])
                      + f"に{count}回先着。"
                      + ("確認済みの比較根拠により今回の◎判定へ反映。"
                         if applied else "◎は従来の能力順位で判断。")
                      + "この条件分岐の将来的中率は未検証。")
    first_corner = holistic.get("firstCorner")
    if first_corner is not None:
        pieces.append("公式記録に基づく初角までの距離は"
                      + str(first_corner["meters"]) + "m。")
    else:
        pieces.append("公式根拠付きの初角までの距離は未取得。推測で内外有利を断定しない。")
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
