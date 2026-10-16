"""ARVEXQ replacement forecast (candidate; must pass regression before deployment).

Uses date-bounded full-career observations and scenario evidence, without the
retired observed 60/40 scorer. Probabilities are deliberately NOT calibrated.
"""
from __future__ import annotations

from copy import deepcopy
from math import exp
from arvexq.prediction.whole_career_scenarios import analyze_race, VERSION as EVIDENCE_VERSION
from arvexq.core.runner_status import is_inactive_runner

VERSION = "arvexq-whole-career-forecast-v2-candidate"
MARKS = ("◎", "○", "▲", "△", "☆", "注")


def _fraction(value, default=0.0):
    try:
        return max(0.0, min(1.0, float(value))) if value is not None else default
    except (ValueError, TypeError):
        return default


def _style(report, name):
    styles = report["observedPositionStyles"]
    return styles.get(name, 0) / max(1, sum(styles.values()))


def _score(report, pressure):
    """Interpretable evidence aggregation, not trained weights or hit rates."""
    win = report["winRate"]
    place = report["top3Rate"]
    if win is None or place is None:
        return None
    n = report["observedStarts"]
    reliability = n / (n + 8.0)
    suited = report["comparableTop3Rate"]
    stable = 0.5 * _fraction(win) + 0.5 * _fraction(place)
    conditions = _fraction(suited, _fraction(place))
    pace = (_style(report, "差し") + _style(report, "追込")) if pressure >= 3 else (
        _style(report, "逃げ") + _style(report, "先行"))
    return reliability * (0.6 * stable + 0.25 * conditions + 0.15 * pace)


def _probabilities(ranked):
    """Ordered-position estimates, explicitly uncalibrated."""
    if len(ranked) < 3:
        return {}
    hi = max(x["score"] for x in ranked)
    weights = [exp(max(-30.0, (x["score"] - hi) / 0.15)) for x in ranked]
    total = sum(weights)
    result = {int(r["horseNumber"]): [0.0, 0.0, 0.0] for r in ranked}
    for i, wi in enumerate(weights):
        p1 = wi / total
        result[int(ranked[i]["horseNumber"])][0] += p1
        for j, wj in enumerate(weights):
            if i == j:
                continue
            p2 = p1 * wj / (total - wi)
            result[int(ranked[j]["horseNumber"])][1] += p2
            for k, wk in enumerate(weights):
                if k not in (i, j):
                    result[int(ranked[k]["horseNumber"])][2] += p2 * wk / (total - wi - wj)
    return {n: {"winProbability": round(v[0], 8),
                "top2Probability": round(v[0] + v[1], 8),
                "top3Probability": round(sum(v), 8),
                "probabilityStatus": "uncalibrated-candidate"} for n, v in result.items()}


def _text(ranked, pressure):
    if not ranked:
        return "各馬の過去走を十分に確認できず、勝ち馬を判断できない。"
    leader = ranked[0]
    situation = ("前へ行きたい馬が複数おり、先行争いが激しくなる可能性がある。"
                 if pressure >= 3 else "序盤の隊列が落ち着き、位置取りと仕掛けが重要となる可能性がある。")
    others = "。対抗馬にも逆転の余地がある。" if len(ranked) >= 2 else "。"
    return (situation + leader.get("name", "本命候補") +
            "は過去の勝ち切りと上位入線の実績を踏まえて中心視する" + others)


def build_forecast(detail):
    """Preserve original sealed forecasts; return an independently scored copy."""
    result = deepcopy(detail)
    reports = analyze_race(result)
    active = [h for h in result.get("horses", []) if isinstance(h, dict)
              and h.get("horseNumber") and not is_inactive_runner(h)]
    lookup = {int(r["horseNumber"]): r for r in reports["horseReports"]}
    rows = []
    for horse in active:
        number = int(horse["horseNumber"])
        report = lookup.get(number)
        score = _score(report, reports["possibleLeadContenders"]) if report else None
        if score is not None:
            rows.append({"horseNumber": number, "name": horse.get("name") or "",
                         "score": score, "report": report})
    rows.sort(key=lambda r: (-r["score"], r["horseNumber"]))
    complete = bool(active) and len(rows) == len(active)
    probability = _probabilities(rows) if complete else {}
    # A missing runner may never be silently ignored to advertise a ready forecast.
    marks = {r["horseNumber"]: MARKS[i] if i < len(MARKS) else ""
             for i, r in enumerate(rows)} if complete else {}
    for horse in result.get("horses", []):
        if not isinstance(horse, dict):
            continue
        no = int(horse.get("horseNumber") or 0)
        e = horse.setdefault("integratedEvaluation", {})
        e["mark"] = marks.get(no, "")
        e["markSource"] = VERSION
        e["markEngineVersion"] = VERSION
        e["honmeiRole"] = "win-axis" if marks.get(no) == "◎" else ""
        e["podiumAxisEligible"] = marks.get(no) == "◎"
        e["modelProbabilities"] = probability.get(no, {})
        e["wholeCareerEvidence"] = lookup.get(no, {})
    head = rows[0] if complete and rows else None
    no = head["horseNumber"] if head else 0
    result["predictionStatus"] = "ready" if complete and len(rows) >= 3 else "insufficient-whole-career-evidence"
    result["predictionModelVersion"] = VERSION
    result["markEngineVersion"] = VERSION
    result["markMethod"] = "全過去走と位置取り、展開、勝ち切り、上位入線の実績を総合判断"
    result["forecastText"] = _text(rows if complete else [], reports["possibleLeadContenders"])
    result["probabilityModelStatus"] = "uncalibrated-candidate"
    result["observedModelCoverage"] = {"horses": len(active), "fullyObserved": len(rows), "allObserved": complete}
    result["factorRanking"] = [{"horseNumber": r["horseNumber"], "name": r["name"], "rank": i + 1,
                                "dominanceScore": round(r["score"] * 100, 2), "modelVersion": VERSION}
                               for i, r in enumerate(rows)]
    result["honmeiDecision"] = {"version": VERSION, "eligible": bool(no), "horseNumber": no,
                                "displayHonmei": bool(no), "confidenceGrade": "C",
                                "role": "win-axis", "axisHorseNumber": no, "fixedAxisAllowed": False}
    result["forecastEvidenceVersion"] = EVIDENCE_VERSION
    return result
