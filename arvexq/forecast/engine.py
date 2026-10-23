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
    """Explain the same six-stage estimate; never run a second predictor.

    Tactical emphasis follows the *publicly described* pace/position approach.
    The model still uses uncalibrated hypothetical scenarios and must say so.
    """
    stages = prediction["stages"]
    styles = stages["runningStyle"]["value"] or {}
    deltas = stages["pace"]["value"] or []
    marks = stages["marks"]["value"] or {}
    ranked = marks.get("orderedWinCandidates") or []
    horses = {h["horseNumber"]: h for h in race["horses"]}
    if not ranked:
        return ""
    def name(no):
        return str(horses.get(no, {}).get("name") or f"{no}番")
    leader = ranked[0]
    front = sorted(
        (no for no, style in styles.items()
         if isinstance(style, (tuple, list)) and len(style) == 4),
        key=lambda no: (-(styles[no][0] + styles[no][1]), no))
    parts = [
        "前走の初角位置・脚質と近走着順を別々に確認し、"
        "同一の展開仮説から勝ち候補・印・買い目を求める。",
        f"勝ち候補の先頭は{name(leader)}。"
        "この順位は未校正のモデル推定で、的中率を保証しない。"
    ]
    if front:
        parts.append("過去の位置取りから前方に運ぶ傾向が強い候補は"
                     + "、".join(name(no) for no in front[:3]) + "。")
    labels = ("標準隊列", "前争いの影響", "前方有利の想定", "後方浮上の想定")
    for index, case in enumerate(deltas):
        if not isinstance(case, dict):
            continue
        favored = sorted(
            ((no, float(delta)) for no, delta in case.items() if delta > 0),
            key=lambda row: (-row[1], row[0]))
        if index == 0:
            parts.append(f"展開仮説{index + 1}（{labels[0]}）を比較対象にする。")
        elif favored:
            parts.append(f"展開仮説{index + 1}（{labels[index] if index < len(labels) else '別想定'}）で"
                         + "補正上位は" + "、".join(name(no) for no, _ in favored[:3]) + "。")
    parts.append("各仮説の発生頻度と予測勝率の実測校正は未完了。"
                 "印と買い目は同じStage64の推定分布から選ぶ。")
    return "".join(parts)


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
