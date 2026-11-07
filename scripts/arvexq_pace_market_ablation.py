#!/usr/bin/env python3
"""Matched pre-off v9b / pace-market research replay (no writes).

Input JSONL: one sealed race per line. Required keys:
  detail             genuine pre-off race payload (no result)
  capturedAt         offset-aware time of pre-off capture
  postAt             offset-aware scheduled start
  baseStrengthsAtSeal  horse number -> frozen original v8 strength (positive)
  v9bWinAtSeal         horse number -> actually published v9b p_win
  winOddsAtSeal        horse number -> authentic pre-off odds
  result               {"finishOrder": [first,second,third,...],
                        "trifectaPayoutPer100": observed yen per 100 yen}
  rawSummary           optional original pre-off summary, else detail

This evaluator FAILS CLOSED if the regenerated v9b baseline does not match
published p_win for every starter (tolerance 0.00011), before any score is
computed. A saved post-race reconstruction is not a valid input.  It cannot
grade the user-reported 194 races without their actual matched seal exports.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from math import isfinite, log
import json
from pathlib import Path

from rewrite.analysis.forecast import RaceForecast, RunnerForecast
from rewrite.analysis.pace_market_candidate import postprocess_pace_market_candidate
from rewrite.analysis.tickets import formation_b_selections, mark_order
from rewrite.data.normalize import normalize_race


def _time(value):
    dt = datetime.fromisoformat(str(value))
    if dt.utcoffset() is None:
        raise ValueError("time must include UTC offset")
    return dt


def _number_map(record):
    return {int(k): float(v) for k, v in record.items()}


def _base(race, strengths):
    return RaceForecast(
        race.race_id, 3. if race.circuit.value == "地方" else 4.,
        "uncalibrated-prior",
        tuple(RunnerForecast(
            number=n, name=r.name.value, ability_score=None,
            strength=float(strengths[n]), pace_adjustment=1.,
            pace_reasons=(), p_win=None, p_top2=None, p_top3=None,
            mark="", status="scored") for r in race.active_runners
            for n in [r.number]),
        "ok")


def _check_record(row):
    required = (
        "detail", "capturedAt", "postAt", "baseStrengthsAtSeal",
        "v9bWinAtSeal", "winOddsAtSeal", "result")
    if any(k not in row for k in required):
        raise ValueError("missing required true sealed evidence")
    if not _time(row["capturedAt"]) < _time(row["postAt"]):
        raise ValueError("not a genuine before-off capture")
    detail = row["detail"]
    if detail.get("result") not in (None, {}, []):
        raise ValueError("post-race result present in pre-off race detail")
    race = normalize_race(row.get("rawSummary") or detail, detail, "frozen-preoff")
    strengths = _number_map(row["baseStrengthsAtSeal"])
    odds = _number_map(row["winOddsAtSeal"])
    published = _number_map(row["v9bWinAtSeal"])
    numbers = {r.number for r in race.active_runners}
    if not (numbers == set(strengths) == set(published)
            and len(numbers) >= 5
            and all(isfinite(x) and x > 0 for x in strengths.values())
            and all(isfinite(x) and 0 <= x <= 1 for x in published.values())):
        raise ValueError("roster/strength/published vector mismatch")
    if any(r.rejected_future_runs for r in race.active_runners):
        raise ValueError("pre-off history contained current/future race")
    finish = row["result"].get("finishOrder")
    payout = float(row["result"].get("trifectaPayoutPer100"))
    if (not isinstance(finish, list) or len(finish) < 3
            or len(set(finish[:3])) != 3
            or any(int(n) not in numbers for n in finish[:3])
            or not isfinite(payout) or payout < 0):
        raise ValueError("invalid real 3連単 result/payout")
    return race, _base(race, strengths), odds, published, tuple(
        int(n) for n in finish[:3]), payout


def _grade(one, result, payout):
    marks = mark_order(one)
    combos = formation_b_selections(marks)
    if not combos:
        raise ValueError("B formation missing")
    winner = result[0]
    ps = {r.number: r.p_win for r in one.runners}
    if winner not in ps or ps[winner] <= 0:
        raise ValueError("winning runner missing from probabilities")
    top = min(ps, key=lambda n: (-ps[n], n))
    hit = tuple(result) in combos
    return {
        "logloss": -log(ps[winner]),
        "top1": int(top == winner),
        "bHit": int(hit),
        "bets": len(combos),
        "bStake": len(combos) * 100,
        "bPayout": payout if hit else 0.,
    }


def _stats(totals):
    rows = list(totals)
    if not rows:
        return None
    stake = sum(r["bStake"] for r in rows)
    return {
        "races": len(rows),
        "logloss": round(sum(r["logloss"] for r in rows) / len(rows), 5),
        "honmeiWinRate": round(sum(r["top1"] for r in rows) / len(rows), 4),
        "bHitRate": round(sum(r["bHit"] for r in rows) / len(rows), 4),
        "bROI": round(sum(r["bPayout"] for r in rows) / stake, 4),
        "totalStakeYen": stake,
        "totalPayoutYen": round(sum(r["bPayout"] for r in rows), 0),
    }


def replay(path: Path, train_through: str):
    # Competing weights require the SAME race inputs, seal-time odds and payout.
    configs = [(0., .5), (.25, .5), (.50, .5), (.25, .25),
               (.50, .25), (.25, 0.), (.50, 0.)]
    series = defaultdict(list)
    seen = set()
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        race, base, odds, published, result, payout = _check_record(
            json.loads(line))
        if race.race_id in seen:
            raise ValueError(f"duplicate race at line {index}")
        seen.add(race.race_id)
        group = "train" if race.date <= train_through else "holdout"
        for pace, market in configs:
            forecast, info = postprocess_pace_market_candidate(
                race, base, win_odds=odds,
                pace_scale=pace, market_weight=market)
            if pace == 0 and market == .5:
                actual = {r.number: r.p_win for r in forecast.runners}
                if any(abs(actual[n] - published[n]) > .00011
                       for n in published):
                    raise ValueError(
                        f"v9b original mismatch at line {index} - do not grade")
            result_row = _grade(forecast, result, payout)
            result_row["paceApplied"] = int(info["paceApplied"])
            series[(race.circuit.value, group, pace, market)].append(result_row)
    report = {
        "source": str(path), "trainingThrough": train_through,
        "guard": "v9b per-horse parity mandatory; no production changes",
        "results": {},
        "selectedFromTrainLogloss": {},
    }
    for circuit in ("中央", "地方"):
        train = []
        for pace, market in configs:
            key = (circuit, "train", pace, market)
            t = _stats(series[key])
            if t:
                train.append((t["logloss"], pace, market))
            label = f"pace={pace},market={market}"
            for group in ("train", "holdout"):
                stats = _stats(series[(circuit, group, pace, market)])
                if stats:
                    report["results"].setdefault(circuit, {}).setdefault(
                        group, {})[label] = stats
        if train:
            _, pace, market = min(train)
            report["selectedFromTrainLogloss"][circuit] = {
                "paceScale": pace, "marketWeight": market,
                "holdout": _stats(series[(circuit, "holdout", pace, market)]),
                "controlHoldout": _stats(series[(circuit, "holdout", 0., .5)]),
            }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sealed_jsonl", type=Path)
    parser.add_argument("--train-through", default="2026-11-05")
    args = parser.parse_args()
    result = replay(args.sealed_jsonl, args.train_through)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
