#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import arvexq_ranker_v209 as v209


def race_order(df: pd.DataFrame) -> list[str]:
    races = df[["race_id", "date"]].drop_duplicates().sort_values(["date", "race_id"])
    return races.race_id.astype(str).tolist()


def make_walk_forward_folds(df: pd.DataFrame, folds: int = 4) -> list[dict]:
    ids = race_order(df)
    n = len(ids)
    if n < 80:
        return []

    test_n = max(12, int(n * 0.10))
    valid_n = max(12, int(n * 0.10))
    out = []
    for k in range(folds, 0, -1):
        test_end = n - (k - 1) * test_n
        test_start = max(0, test_end - test_n)
        valid_end = test_start
        valid_start = max(0, valid_end - valid_n)
        train_end = valid_start
        if train_end < max(40, test_n * 2):
            continue
        train = ids[:train_end]
        valid = ids[valid_start:valid_end]
        test = ids[test_start:test_end]
        if not train or not valid or not test:
            continue
        out.append({
            "train": set(train),
            "valid": set(valid),
            "test": set(test),
            "train_n": len(train),
            "valid_n": len(valid),
            "test_n": len(test),
        })
    return out


def weighted_metrics(rows: list[dict]) -> dict:
    total = sum(int(x.get("races") or 0) for x in rows)
    if total <= 0:
        return {"races": 0, "top1": 0.0, "top3": 0.0, "mrr": 0.0}
    return {
        "races": total,
        "top1": sum(float(x.get("top1") or 0) * int(x.get("races") or 0) for x in rows) / total,
        "top3": sum(float(x.get("top3") or 0) * int(x.get("races") or 0) for x in rows) / total,
        "mrr": sum(float(x.get("mrr") or 0) * int(x.get("races") or 0) for x in rows) / total,
    }


def race_margin_table(df: pd.DataFrame, score: str) -> pd.DataFrame:
    rows = []
    for rid, g in df.groupby("race_id"):
        g = g.sort_values(score, ascending=False)
        if len(g) < 2:
            continue
        top = g.iloc[0]
        second = g.iloc[1]
        market = g.sort_values("market_prob", ascending=False).iloc[0] if float(g.market_prob.max()) > 0 else None
        baseline = g.sort_values("p1", ascending=False).iloc[0]
        rows.append({
            "race_id": rid,
            "margin": float(top[score] - second[score]),
            "win": int(top.finish) == 1,
            "top3": int(top.finish) <= 3,
            "model_market_agree": bool(market is not None and int(top.horse_no) == int(market.horse_no)),
            "triple_agree": bool(
                market is not None
                and int(top.horse_no) == int(market.horse_no)
                and int(top.horse_no) == int(baseline.horse_no)
            ),
        })
    return pd.DataFrame(rows)


def confidence_eval(valid: pd.DataFrame, hold: pd.DataFrame, score: str) -> dict:
    vr = race_margin_table(valid, score)
    hr = race_margin_table(hold, score)
    if vr.empty or hr.empty:
        return {}
    threshold = float(vr.margin.quantile(0.75))

    def metric(q: pd.DataFrame) -> dict:
        if q.empty:
            return {"races": 0, "top1": 0.0, "top3": 0.0}
        return {"races": len(q), "top1": float(q.win.mean()), "top3": float(q.top3.mean())}

    return {
        "validationMarginQ75": threshold,
        "highMargin": metric(hr[hr.margin >= threshold]),
        "modelMarketAgree": metric(hr[hr.model_market_agree]),
        "agreeHighMargin": metric(hr[(hr.model_market_agree) & (hr.margin >= threshold)]),
        "tripleAgree": metric(hr[hr.triple_agree]),
        "tripleAgreeHighMargin": metric(hr[(hr.triple_agree) & (hr.margin >= threshold)]),
    }


def one_fold(d: pd.DataFrame, spec: dict) -> dict:
    train_ids, valid_ids, test_ids = spec["train"], spec["valid"], spec["test"]
    models = v209.fit_models(d, train_ids)
    valid = d[d.race_id.isin(valid_ids)].copy()
    hold = d[d.race_id.isin(test_ids)].copy()
    hold["baseline"] = hold.p1

    fold = {
        "train": spec["train_n"],
        "valid": spec["valid_n"],
        "test": spec["test_n"],
        "dateRange": {
            "valid": [str(valid.date.min()), str(valid.date.max())],
            "test": [str(hold.date.min()), str(hold.date.max())],
        },
        "baselineAll": v209.metrics_for(hold, "baseline"),
        "models": {},
    }

    for name, model in models.items():
        valid[name] = model.predict(valid[v209.FEATURES])
        hold[name] = model.predict(hold[v209.FEATURES])
        pure = v209.metrics_for(hold, name)
        tuned = v209.tune_blend(valid, name)
        model_out = {"pure": pure, "blend": None}
        if tuned:
            _, temp, alpha, valid_metric = tuned
            vq = v209.add_market(v209.add_model_prob(valid, name, temp))
            vq = vq[vq.market_prob > 0].copy()
            vq["blend"] = alpha * vq.model_prob + (1 - alpha) * vq.market_prob

            hq = v209.add_market(v209.add_model_prob(hold, name, temp))
            hq = hq[hq.market_prob > 0].copy()
            hq["blend"] = alpha * hq.model_prob + (1 - alpha) * hq.market_prob
            hq["baselineEligible"] = hq.p1

            model_out["blend"] = {
                "alphaModel": float(alpha),
                "temperature": float(temp),
                "validation": valid_metric,
                "holdout": v209.metrics_for(hq, "blend"),
                "baselineEligible": v209.metrics_for(hq, "baselineEligible"),
                "marketOnly": v209.metrics_for(hq, "market_prob"),
                "confidence": confidence_eval(vq, hq, "blend"),
            }
        fold["models"][name] = model_out
    return fold


def summarize_folds(folds: list[dict], model_name: str) -> dict:
    pure = [f["models"][model_name]["pure"] for f in folds]
    blends = [f["models"][model_name].get("blend") for f in folds]
    blends = [b for b in blends if b]
    blend_metrics = [b["holdout"] for b in blends]
    baseline_eligible = [b["baselineEligible"] for b in blends]
    market_only = [b["marketOnly"] for b in blends]

    improvements = []
    for b in blends:
        improvements.append({
            "top1Delta": float(b["holdout"]["top1"] - b["baselineEligible"]["top1"]),
            "top3Delta": float(b["holdout"]["top3"] - b["baselineEligible"]["top3"]),
            "beatBaselineTop1": bool(b["holdout"]["top1"] > b["baselineEligible"]["top1"]),
            "beatMarketTop1": bool(b["holdout"]["top1"] > b["marketOnly"]["top1"]),
        })

    conf_keys = ["highMargin", "modelMarketAgree", "agreeHighMargin", "tripleAgree", "tripleAgreeHighMargin"]
    conf = {}
    for key in conf_keys:
        rows = []
        for b in blends:
            c = (b.get("confidence") or {}).get(key)
            if c:
                rows.append(c)
        conf[key] = weighted_metrics(rows) if rows else {"races": 0, "top1": 0.0, "top3": 0.0, "mrr": 0.0}

    return {
        "pure": weighted_metrics(pure),
        "blend": weighted_metrics(blend_metrics),
        "baselineEligible": weighted_metrics(baseline_eligible),
        "marketOnly": weighted_metrics(market_only),
        "folds": len(folds),
        "beatBaselineTop1Folds": sum(1 for x in improvements if x["beatBaselineTop1"]),
        "beatMarketTop1Folds": sum(1 for x in improvements if x["beatMarketTop1"]),
        "meanTop1DeltaVsBaseline": float(np.mean([x["top1Delta"] for x in improvements])) if improvements else 0.0,
        "meanTop3DeltaVsBaseline": float(np.mean([x["top3Delta"] for x in improvements])) if improvements else 0.0,
        "confidence": conf,
    }


def circuit_run(df: pd.DataFrame, circuit: str, folds_n: int) -> dict:
    d = df[df.circuit == circuit].copy()
    specs = make_walk_forward_folds(d, folds_n)
    if not specs:
        return {"error": "insufficient", "races": d.race_id.nunique()}
    folds = [one_fold(d, spec) for spec in specs]
    return {
        "races": d.race_id.nunique(),
        "foldCount": len(folds),
        "folds": folds,
        "summary": {
            "lightgbm": summarize_folds(folds, "lightgbm"),
            "catboost": summarize_folds(folds, "catboost"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--extra-jra")
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--out", default="ranker-v210.json")
    args = ap.parse_args()

    details = v209.load_d1(args.days) + v209.load_extra(args.extra_jra)
    rows = v209.rows_from_details(details)
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("no usable rows")

    report = {
        "generatedAt": datetime.now(v209.JST).isoformat(),
        "method": "expanding walk-forward with validation-tuned market blend",
        "foldsRequested": args.folds,
        "featureCount": len(v209.FEATURES),
        "features": v209.FEATURES,
        "leakageGuard": {
            "chronological": True,
            "futureInTrain": False,
            "resultAsFeature": False,
            "payoutAsFeature": False,
            "oddsInPureRanker": False,
            "oddsOnlyPostModelCalibration": True,
            "confidenceThresholdFromValidationOnly": True,
            "baselineComparedOnSameMarketEligibleRaces": True,
        },
        "circuits": {},
    }
    for circuit in ("中央", "地方"):
        report["circuits"][circuit] = circuit_run(df, circuit, args.folds)
        print(circuit, json.dumps(report["circuits"][circuit]["summary"], ensure_ascii=False))

    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
