"""Master 18-section pre-off audit and ticket comparison.

Additive, deterministic decision evidence for the rewrite publisher. It never
changes frozen marks, replays race results or invents missing odds. The 100
point rubric and pace scenarios are UNFITTED research hypotheses until a
separately registered out-of-time test establishes their predictive value.
"""
from __future__ import annotations

from itertools import combinations
from math import fsum, isfinite

from .ability import LOWER_IS_BETTER, _minmax, extract_features
from .pace import style_profile
from ..safety.probability import distribution, ticket_probability

VERSION = "master18-candidate-v1"
# User-specified nine categories; never give missing evidence free points.
RUBRIC = {
    "baseAbility": (24, {"speed": 14, "class_recent": 10}),
    "recentForm": (15, {"form": 9, "consistency": 6}),
    "courseDistance": (14, {"distance": 9, "track": 5}),
    "paceFit": (15, {"closing": 9, "pace": 6}),
    "goingFit": (8, {"surface": 4, "condition": 4}),
    "trainingCondition": (8, {}),  # no verified workout fields in normalized record
    "jockeyStable": (6, {"jockey": 6}),  # rider evidence only; stable unavailable
    "drawFit": (4, {}),  # no verified, course-specific draw bias
    "weightRest": (6, {"rest": 3, "weight_shift": 3}),
}
assert sum(weight for weight, _ in RUBRIC.values()) == 100


def _ranked(values: dict[int, float], reverse: bool = False) -> dict[int, float]:
    return _minmax(values, reverse)


def _observations(race, pace) -> tuple[dict[int, dict[str, float]], dict[int, dict]]:
    active = tuple(race.active_runners)
    features = {r.number: extract_features(race, r) for r in active}
    profiles = {r.number: style_profile(r) for r in active}
    name = {r.number: r.name.value for r in active}
    raw = {r.number: dict(features[r.number].raw) for r in active}
    # PaceFit is a position-based, intentionally uncalibrated signal. Do not
    # infer it from gate draw, popularity or any race result after this date.
    for number, profile in profiles.items():
        if profile.start_ratio is not None and profile.closing_gain is not None:
            raw[number]["pace"] = max(0.0, min(1.0,
                (1.0 - profile.start_ratio) * 0.5 +
                max(0.0, min(1.0, 0.5 + profile.closing_gain)) * 0.5))
    normalized: dict[int, dict[str, float]] = {n: {} for n in raw}
    keys = {key for _, parts in RUBRIC.values() for key in parts}
    for key in keys:
        present = {n: vals[key] for n, vals in raw.items()
                   if isinstance(vals.get(key), (int, float))
                   and isfinite(vals[key])}
        for number, score in _ranked(present, key in LOWER_IS_BETTER).items():
            normalized[number][key] = score
    detail = {}
    for number, f in features.items():
        p = profiles[number]
        if p.basis_runs == 0:
            style = "脚質不定"
        elif p.start_ratio <= 0.15:
            style = "逃げ候補"
        elif p.start_ratio <= 0.35:
            style = "先行"
        elif p.start_ratio <= 0.55:
            style = "好位差し"
        elif p.start_ratio <= 0.8:
            style = "差し"
        else:
            style = "追い込み"
        detail[number] = {
            "name": name[number], "style": style,
            "observedRuns": f.evidence_runs, "cornerEvidenceRuns": p.basis_runs,
            "rejectedFutureRuns": next(r.rejected_future_runs for r in active
                                       if r.number == number),
        }
    return normalized, detail


def _score_card(values: dict[str, float]) -> dict:
    breakdown = {}
    earned, available = 0.0, 0
    for category, (maximum, parts) in RUBRIC.items():
        observed = sum(weight for feature, weight in parts if feature in values)
        points = sum(weight * values[feature] for feature, weight in parts
                     if feature in values)
        # A 100-point total is the maximum, not a claim that every part was observed.
        breakdown[category] = {
            "earned": round(points, 2), "possibleObserved": observed,
            "maximum": maximum,
            "status": "missing" if not observed else
                      "partial" if observed < maximum else "observed",
        }
        earned += points
        available += observed
    return {
        "observedPoints": round(earned, 2),
        "possibleObserved": available,
        "maximum": 100,
        "range": [round(earned, 2), round(earned + 100 - available, 2)],
        "unvalidated": True,
        "categories": breakdown,
    }


def _scenario_comparison(race, forecast, pace) -> dict:
    by_number = {r.number: r for r in forecast.runners
                 if r.strength is not None and r.strength > 0}
    profiles = {r.number: style_profile(r) for r in race.active_runners}
    # These deliberately small sensitivity factors are hypotheses, not
    # empirically estimated pace frequencies or probabilities.
    factor = {"slow": (1.08, 0.96), "normal": (1.0, 1.0),
              "fast": (0.92, 1.08)}
    rankings = {}
    for scenario, (front_factor, closer_factor) in factor.items():
        adjusted = {}
        for n, r in by_number.items():
            p = profiles[n]
            adjustment = 1.0
            if p.start_ratio is not None and p.start_ratio <= 0.35:
                adjustment *= front_factor
            if p.closing_gain is not None and p.closing_gain > 0.05:
                adjustment *= closer_factor
            adjusted[n] = r.strength * adjustment
        rankings[scenario] = sorted(adjusted, key=lambda n: (-adjusted[n], n))
    eligible = set.intersection(*(set(numbers[:3]) for numbers in rankings.values())) if rankings else set()
    return {
        "status": "sensitivity-unvalidated",
        "scenarioFrequencies": None,
        "likelyPace": pace.pace_label,
        "rankings": rankings,
        "top3AcrossAllScenarios": sorted(eligible),
        "stages": {
            name: [n for n, _ratio in pace.stages[name].order]
            for name in ("start", "corner3", "corner4", "straight")
        },
        "unknownPositionNumbers": list(pace.unknown_runners),
    }


def _ticket_profiles(race, forecast, odds_by_kind=None):
    odds_by_kind = odds_by_kind or {}
    strengths = {r.number: r.strength for r in forecast.runners
                 if r.strength is not None and r.strength > 0}
    if len(strengths) < 3:
        return {"status": "insufficient-evidence", "profiles": [],
                "decision": "見送り", "reason": "着順分布を計算できない"}
    joint = distribution(strengths)
    margin = {r.number: r for r in forecast.runners}
    top = sorted(strengths, key=lambda n: (-(margin[n].p_top3 or 0), n))
    win_rank = sorted(strengths, key=lambda n: (-(margin[n].p_win or 0), n))
    n = len(strengths)
    offered = []
    if n >= 5:
        place_slots = 2 if n <= 7 else 3
        for number in top[:5]:
            offered.append(("複勝", "place", (number,), place_slots))
    for pair in combinations(top[:min(6, n)], 2):
        offered.append(("ワイド", "wide", pair, 3))
        offered.append(("馬連", "quinella", pair, 3))
    for trio in combinations(top[:min(6, n)], 3):
        offered.append(("3連複", "trio", trio, 3))
    scored = []
    for label, kind, horses, slots in offered:
        p = ticket_probability(joint, kind, horses, place_count=slots)
        actual = odds_by_kind.get(label, {}).get("-".join(map(str, horses)))
        if type(actual) not in (int, float) or not isfinite(actual) or actual < 1.0:
            actual = None
        # This is a mathematical break-even odds threshold, NOT expected ROI.
        scored.append({"kind": label, "numbers": list(horses),
                       "probabilityEstimate": round(p, 4),
                       "breakEvenOddsEstimate": round(1 / p, 2) if p else None,
                       "actualOdds": actual,
                       "expectedReturn": None,
                       "probabilityStatus": "model-estimate-not-independently-validated"})
    def best(group):
        if not group:
            return None
        return max(group, key=lambda t: (t["probabilityEstimate"],
                                         -len(t["numbers"]),
                                         tuple(-n for n in t["numbers"])))
    hit = best([s for s in scored if s["kind"] in ("複勝", "ワイド")])
    balance = best([s for s in scored if s["kind"] in ("ワイド", "馬連", "3連複")
                    and s["actualOdds"] is not None])
    # An outsider MUST be a demonstrated market-vs-model discrepancy.
    actual_win = {r.number: r.win_odds.value for r in race.active_runners
                  if r.win_odds.present and type(r.win_odds.value) in (int, float)
                  and isfinite(r.win_odds.value) and r.win_odds.value > 1}
    outsiders = []
    if len(actual_win) == n:
        market_order = sorted(actual_win, key=lambda x: (actual_win[x], x))
        for idx, number in enumerate(win_rank):
            market_position = market_order.index(number)
            if market_position >= 4 and market_position - idx >= 2:
                outsiders.append(number)
    hole = best([s for s in scored if s["kind"] == "ワイド"
                 and any(n in outsiders for n in s["numbers"])])
    selected = []
    for label, item in (("的中率最優先", hit), ("的中率・回収率バランス", balance),
                        ("穴馬型", hole)):
        selected.append({"type": label, "candidate": item,
                         "status": "comparison-only" if item else "no-supported-candidate"})
    return {
        "status": "uncalibrated-ticket-comparison",
        "profiles": selected, "outsiderNumbers": outsiders,
        "referenceBudgetYen": 1000, "stakeAdvice": None,
        "decision": "見送り",
        "reason": "券種別の実オッズ・独立した予測確率検証が揃うまで購入推奨しない",
        "note": "独立した着順の同時確率から比較。確率の加算・掛け算による重複計上をしない",
    }


def analyze_master18(race, forecast, pace, *, odds_by_kind=None) -> dict:
    """Build an inspectable, all-runner audit from facts available before post."""
    if race.race_id != forecast.race_id or race.race_id != pace.race_id:
        raise ValueError("race identity mismatch")
    normalized, detail = _observations(race, pace)
    forecast_by_number = {r.number: r for r in forecast.runners}
    if set(normalized) != set(forecast_by_number):
        raise ValueError("active roster and forecast mismatch")
    all_cards = []
    for r in race.runners:
        if r.scratched:
            all_cards.append({"number": r.number, "name": r.name.value,
                              "status": "scratched", "mark": None})
            continue
        f = forecast_by_number[r.number]
        card = _score_card(normalized[r.number])
        card.update({
            "number": r.number, "name": r.name.value, "status": f.status,
            "mark": f.mark,
            "winProbability": f.p_win,
            "top2Probability": f.p_top2,
            "top3Probability": f.p_top3,
            **detail[r.number],
        })
        all_cards.append(card)
    ranked = sorted(
        (c for c in all_cards if c["status"] != "scratched"),
        key=lambda c: (-(c["top3Probability"] or 0), c["number"]))
    for i, card in enumerate(ranked, 1):
        card["top3Rank"] = i
    n = len(ranked)
    race_odds = {
        r.number: r.win_odds.value for r in race.active_runners
        if r.win_odds.present and type(r.win_odds.value) in (int, float)
        and isfinite(r.win_odds.value) and r.win_odds.value > 1
    }
    market = {"status": "incomplete", "rankings": [], "cautions": []}
    if len(race_odds) == n and n:
        order = sorted(race_odds, key=lambda num: (race_odds[num], num))
        probability_order = sorted(ranked, key=lambda c: (-(
            c["winProbability"] or 0), c["number"]))
        model_rank = {c["number"]: i for i, c in enumerate(probability_order)}
        cautions = []
        for i, number in enumerate(order):
            diff = i - model_rank[number]
            if i < 3 and diff <= -2:
                cautions.append({"number": number, "type": "overrated-market-favourite",
                                 "marketRank": i + 1, "modelRank": model_rank[number] + 1})
        market = {"status": "full-live-odds-snapshot",
                  "rankings": order, "cautions": cautions,
                  "note": "市場評価と予測の非独立性に注意（v9bはオッズ融合）"}
    paces = _scenario_comparison(race, forecast, pace)
    ticket = _ticket_profiles(race, forecast, odds_by_kind)
    coverage = round(fsum(c["possibleObserved"] for c in ranked) /
                     (100 * len(ranked)), 3) if ranked else 0.0
    grade = ("D" if coverage < .35 else "C" if coverage < .60
             else "B")
    return {
        "version": VERSION, "raceId": race.race_id,
        "mode": race.segment.value,
        "status": "unvalidated-candidate",
        "rubric": {k: weight for k, (weight, _) in RUBRIC.items()},
        "scoreMeaning": "observed points out of 100; unobserved points stay missing",
        "allRunners": all_cards,
        "top3Ranking": [r["number"] for r in ranked],
        "paceSensitivity": paces,
        "marketComparison": market,
        "tickets": ticket,
        "confidence": {"grade": grade, "measured": False,
                       "featureCoverage": coverage,
                       "largestUncertainty": "未検証の配点と展開変化・未取得情報"},
        "counterChecks": {
            "honmeiLossScenarios": ["出遅れ", "馬場変化", "想定を超える先行争い"],
            "rivalUpset": "対抗の展開優位を別途確認",
            "outsiderEvidence": "市場・モデルの順位差のみで穴馬を断定しない",
            "goingChange": "良馬場・道悪の条件分岐は観測データ不足なら未判定",
            "paceChange": "slow/normal/fastの順位感度を参照",
            "oddsChange": "券種別オッズを再取得して採否を再計算",
            "missingness": "全頭のpossibleObservedと範囲で明示",
            "consistency": "印・確率は同一の保存済み予想原本を参照",
        },
        "probabilityVerification": forecast.probability_status,
        "productionMarksChanged": False,
    }
