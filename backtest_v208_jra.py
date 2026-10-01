#!/usr/bin/env python3
"""ARVEXQ v208: JRA-only leakage-guarded backtest and model search.

Fast path:
1) Reuse any finalized JRA snapshots already stored in ARVEXQ D1.
2) If D1 does not have enough JRA history, supplement directly from JRA official
   historical cards/results through the production app's existing JRA parser.
3) Strip the current-race result and market fields *before* computing model inputs.
4) Optimize chronologically (Train -> Validation -> Holdout), then report global
   and sufficiently large JRA surface/track/distance candidates.

The result is never used as a feature. It is reattached only after scoring so it
can serve as the evaluation label.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import sys
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import backtest_v206 as core

MODEL_VERSION = "arvexq-jra-backtest-2026.10-v208r1"
SEED = 208


def is_central(detail: dict) -> bool:
    return str(detail.get("circuit") or "") == "中央" or str(detail.get("id") or "").startswith("jra-")


def sanitize_for_scoring(detail: dict) -> tuple[dict, dict] | tuple[None, None]:
    result = copy.deepcopy(detail.get("result") or {})
    if len(result.get("finishers") or []) < 3:
        return None, None
    pre = copy.deepcopy(detail)
    pre["circuit"] = "中央"
    pre["result"] = None
    pre.pop("raceStatus", None)
    pre.pop("payouts", None)
    # Market fields are display-only and forbidden as model inputs.
    for h in pre.get("horses") or []:
        for k in ("winOdds", "popularity", "marketProbability", "oddsSource"):
            h.pop(k, None)
        # Defensive cleanup in case a scraper ever adds current-race result fields.
        for k in ("finishPosition", "resultTime", "currentFinish", "currentResult"):
            h.pop(k, None)
    return pre, result


def prepare_official_snapshot(prod, summary: dict) -> dict | None:
    """Build a historical JRA snapshot without depending on the live JRA homepage.

    Historical enumeration comes from netkeiba's date race list because the JRA
    live CNAME discovery in production is intentionally optimized for the current
    meeting.  The current-race market fields are stripped before scoring, and the
    historical result is attached only after the pre-race feature build.
    """
    rid = str(summary.get("id") or "")
    if not rid:
        return None
    d = copy.deepcopy(summary)
    d["circuit"] = "中央"
    d.setdefault("horses", [])

    # Historical entry card: use the production netkeiba parser directly.  It
    # carries the same past-run evidence used by the live central fallback.
    try:
        if not (d.get("horses") or []):
            rows = prod._netkeiba_detail_rows(d) or []
            if rows:
                d["horses"] = rows
                d["fieldSize"] = len(rows)
    except Exception as exc:
        print("JRA historical card failed", rid, exc, file=sys.stderr)
        return None
    if not (d.get("horses") or []):
        return None

    # Historical result is an evaluation label only.  It is removed immediately
    # by sanitize_for_scoring() before any model feature is calculated.
    try:
        rr = prod._netkeiba_current_result(d)
    except Exception as exc:
        print("JRA historical result failed", rid, exc, file=sys.stderr)
        rr = None
    if not isinstance(rr, dict) or len(rr.get("finishers") or []) < 3:
        return None
    d["result"] = rr

    pre, label = sanitize_for_scoring(d)
    if pre is None:
        return None
    try:
        # Recompute the exact pre-race evidence model with current result/market
        # fields already removed.  No post-race value can enter these features.
        pre = prod._strip_excluded(prod._apply_enrichment(rid, pre))
        pre = prod._attach_stored_career(pre)
        pre = prod._precompute_detail_metrics(prod._attach_evaluation_context(pre))
    except Exception as exc:
        print("JRA pre-race metric build failed", rid, exc, file=sys.stderr)
        return None
    pre["result"] = label
    pre["circuit"] = "中央"
    return pre


def collect_d1_central(api_url: str, days: int, outdir: Path) -> tuple[list[core.RaceRow], list[dict], set[str]]:
    today = datetime.now(core.JST).date()
    races: list[core.RaceRow] = []
    daily: list[dict] = []
    ids: set[str] = set()
    for offset in range(1, days + 1):
        ds = (today - timedelta(days=offset)).isoformat()
        url = api_url.rstrip("/") + "/api/day?" + urllib.parse.urlencode({"date": ds, "details": "1"})
        try:
            payload = core.api_json(url, timeout=16, retries=2)
        except Exception as exc:
            daily.append({"date": ds, "d1Central": 0, "error": str(exc)[:160]})
            continue
        added = 0
        for d in payload.get("details") or []:
            if not isinstance(d, dict) or not is_central(d):
                continue
            rr = core.race_from_detail(d)
            if rr:
                rr.circuit = "中央"
                races.append(rr); ids.add(rr.race_id); added += 1
        if added:
            print(f"{ds}: D1 JRA usable={added}")
        daily.append({"date": ds, "d1Central": added, "error": ""})
    return races, daily, ids


def jra_candidate_dates(days: int):
    today = datetime.now(core.JST).date()
    # JRA is overwhelmingly Sat/Sun; Mondays catch most holiday meetings.
    dates = []
    for offset in range(days, 0, -1):
        d = today - timedelta(days=offset)
        if d.weekday() in (0, 5, 6):
            dates.append(d)
    return dates


def evenly_limit(rows: list[dict], maximum: int) -> list[dict]:
    if maximum <= 0 or len(rows) <= maximum:
        return rows
    if maximum == 1:
        return [rows[-1]]
    idx = sorted({round(i * (len(rows) - 1) / (maximum - 1)) for i in range(maximum)})
    return [rows[i] for i in idx]


def collect_jra_official(days: int, max_races: int, skip_ids: set[str], outdir: Path, workers: int = 6) -> tuple[list[core.RaceRow], list[dict]]:
    try:
        import app as prod
    except Exception as exc:
        print("Could not import production app for JRA official supplement:", exc, file=sys.stderr)
        return [], []

    summaries: list[dict] = []
    calendar_rows: list[dict] = []
    for d in jra_candidate_dates(days):
        ds = d.isoformat()
        try:
            # Production JRA CNAME discovery is tuned for today's meeting and can
            # return zero on historical dates.  Enumerate historical JRA race IDs
            # from the date race list instead; detail/result fetches remain isolated
            # and market/result fields are forbidden from model inputs.
            rows = prod._netkeiba_race_summaries(ds) or []
            if not rows:
                rows = prod.fetch_jra_official(ds, lightweight=True) or []
        except Exception as exc:
            calendar_rows.append({"date": ds, "summaryCount": 0, "error": str(exc)[:160]})
            continue
        rows = [dict(r, circuit="中央") for r in rows if r.get("id") and str(r.get("id")).startswith("jra-")]
        fresh = [r for r in rows if str(r.get("id")) not in skip_ids]
        summaries.extend(fresh)
        calendar_rows.append({"date": ds, "summaryCount": len(rows), "freshCount": len(fresh), "error": ""})
        if rows:
            print(f"{ds}: JRA program={len(rows)} fresh={len(fresh)}")

    summaries.sort(key=lambda r: (str(r.get("date") or ""), str(r.get("track") or ""), int(r.get("raceNumber") or 0)))
    summaries = evenly_limit(summaries, max_races)
    print("JRA official detail targets:", len(summaries))

    details: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as ex:
        futures = {ex.submit(prepare_official_snapshot, prod, r): r for r in summaries}
        done = 0
        for fut in as_completed(futures):
            try:
                d = fut.result()
            except Exception as exc:
                d = None
                print("JRA worker failed", exc, file=sys.stderr)
            done += 1
            if d:
                details.append(d)
            if done % 25 == 0 or done == len(futures):
                print(f"JRA detail progress {done}/{len(futures)} usable={len(details)}")

    # Keep a compact raw snapshot so rerun diagnostics are inspectable in the artifact.
    (outdir / "jra-official-snapshots.json").write_text(json.dumps({"details": details}, ensure_ascii=False), encoding="utf-8")
    races: list[core.RaceRow] = []
    for d in details:
        rr = core.race_from_detail(d)
        if rr:
            rr.circuit = "中央"
            races.append(rr)
    return races, calendar_rows


def surface_key(r: core.RaceRow) -> str:
    s = str(r.surface or "")
    if "障" in s: return "surface:障害"
    if "ダ" in s: return "surface:ダート"
    if "芝" in s: return "surface:芝"
    return "surface:不明"


def distance_key(r: core.RaceRow) -> str:
    d = r.distance
    if d <= 1400: b = "<=1400"
    elif d <= 1800: b = "1500-1800"
    elif d <= 2200: b = "1900-2200"
    else: b = ">=2300"
    return f"distance:{b}"


def optimize_segments(races: list[core.RaceRow], iterations: int, seed: int) -> dict:
    groups: dict[str, list[core.RaceRow]] = defaultdict(list)
    for r in races:
        groups[surface_key(r)].append(r)
        groups[distance_key(r)].append(r)
        if r.track:
            groups[f"track:{r.track}"].append(r)
        # Surface + distance is useful when enough samples exist.
        groups[f"{surface_key(r)}|{distance_key(r)}"].append(r)
    out = {}
    for idx, (name, rs) in enumerate(sorted(groups.items())):
        if len(rs) < 60:
            continue
        w, search = core.optimize(rs, max(500, iterations // 3), seed + (idx + 1) * 131)
        _, valid, hold = core.split_time(rs)
        evalset = hold if hold else valid
        promo = core.promotion_decision(evalset, w)
        out[name] = {"races": len(rs), "weights": w, "promotion": promo, "search": search}
    return out


def write_report(outdir: Path, races: list[core.RaceRow], candidate: dict[str, float], search: dict, promo: dict,
                 segments: list[dict], specialized: dict, tickets_base: dict, tickets_candidate: dict,
                 daily: list[dict], calendar_rows: list[dict]) -> None:
    _, valid, hold = core.split_time(races)
    evalset = hold if hold else valid if valid else races
    b = core.metric_block(evalset, baseline=True)
    c = core.metric_block(evalset, candidate)
    payload = {
        "version": MODEL_VERSION,
        "generatedAt": datetime.now(core.JST).isoformat(),
        "raceCount": len(races),
        "evaluationRaceCount": len(evalset),
        "leakageGuard": {
            "resultUsedAsFeature": False,
            "oddsUsedAsFeature": False,
            "popularityUsedAsFeature": False,
            "resultRemovedBeforeProductionScoring": True,
            "inputFeatureWhitelist": core.FEATURES,
        },
        "baseline": b,
        "candidate": c,
        "promotion": promo,
        "search": search,
        "candidateWeights": candidate,
        "specializedCandidates": specialized,
        "segments": segments,
        "tickets": {"baseline": tickets_base, "candidate": tickets_candidate},
        "d1Daily": daily,
        "jraCalendar": calendar_rows,
    }
    (outdir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "candidate_model_v208_jra.json").write_text(json.dumps({
        "version": MODEL_VERSION,
        "scope": "中央",
        "global": {"weights": candidate, "promotion": promo},
        "specialized": specialized,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    with (outdir / "segments.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["segment","races","baselineTop1","candidateTop1","deltaTop1","baselineTop3","candidateTop3","deltaTop3","baselineMRR","candidateMRR"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(segments)

    with (outdir / "race_audit.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["date","track","surface","distance","raceNo","raceId","winner","baselinePick","candidatePick","baselineWinnerRank","candidateWinnerRank"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in races:
            br = core.race_rank(r, baseline=True); cr = core.race_rank(r, candidate)
            w.writerow({
                "date": r.race_date, "track": r.track, "surface": r.surface, "distance": r.distance,
                "raceNo": r.race_no, "raceId": r.race_id, "winner": r.winner,
                "baselinePick": br[0] if br else "", "candidatePick": cr[0] if cr else "",
                "baselineWinnerRank": br.index(r.winner)+1 if r.winner in br else 999,
                "candidateWinnerRank": cr.index(r.winner)+1 if r.winner in cr else 999,
            })

    lines = ["# ARVEXQ v208 中央専用バックテスト", ""]
    lines.append(f"- 中央/JRA 有効レース: **{len(races)}** / 最終評価(Holdout): **{len(evalset)}**")
    lines.append("- 現レースの結果・払戻・オッズ・人気は**モデル入力に不使用**。公式結果は採点ラベルだけに使用。")
    lines.append(f"- 判定: **{'採用候補' if promo.get('promote') else 'まだ採用しない'}** — {promo.get('reason','')}")
    lines += ["", "## 勝ち馬順位", "", "| 指標 | 現行中央P1 | v208候補 | 差 |", "|---|---:|---:|---:|"]
    for key, label in [("top1","◎相当1着率"),("top3","勝ち馬Top3"),("top5","勝ち馬Top5"),("mrr","平均逆順位(MRR)")]:
        bv, cv = b[key], c[key]
        if key == "mrr": lines.append(f"| {label} | {bv:.3f} | {cv:.3f} | {cv-bv:+.3f} |")
        else: lines.append(f"| {label} | {core.fmt_pct(bv)} | {core.fmt_pct(cv)} | {core.fmt_pct(cv-bv)} |")

    lines += ["", "## 券種別（100円/点シミュレーション）", "", "| 券種 | 現行Hit | v208 Hit | 現行平均点数 | v208平均点数 | v208 ROI* |", "|---|---:|---:|---:|---:|---:|"]
    kinds = [k for k in ["ワイド","馬連","馬単","3連複","3連単"] if k in tickets_base or k in tickets_candidate]
    for k in kinds:
        tb, tc = tickets_base.get(k, {}), tickets_candidate.get(k, {})
        roi = tc.get("roi")
        lines.append(f"| {k} | {core.fmt_pct(tb.get('hitRate',0))} ({tb.get('issued',0)}) | {core.fmt_pct(tc.get('hitRate',0))} ({tc.get('issued',0)}) | {tb.get('avgPoints',0):.2f} | {tc.get('avgPoints',0):.2f} | {'—' if roi is None else core.fmt_pct(roi)} |")

    lines += ["", "## 中央セグメント候補", "", "| 区分 | R | 採用候補 | Holdout Top1差 | 理由 |", "|---|---:|---|---:|---|"]
    for name, z in sorted(specialized.items(), key=lambda kv: (-kv[1].get("races",0), kv[0]))[:30]:
        p = z.get("promotion") or {}; bb = (p.get("baseline") or {}).get("top1",0); cc = (p.get("candidate") or {}).get("top1",0)
        lines.append(f"| {name} | {z.get('races',0)} | {'YES' if p.get('promote') else 'NO'} | {core.fmt_pct(cc-bb)} | {p.get('reason','')} |")
    lines += ["", "`candidate_model_v208_jra.json` が中央本番候補。採用判定はHoldoutだけで決めます。", ""]
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def collect_files(paths: list[str]) -> list[core.RaceRow]:
    races = core.collect_files(paths)
    return [r for r in races if r.circuit == "中央" or r.race_id.startswith("jra-")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-url", default=os.getenv("ARVEXQ_API_URL", "https://kraiz-api.4b89h4fydd.workers.dev"))
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--max-races", type=int, default=360)
    ap.add_argument("--iterations", type=int, default=2500)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="backtest-v208-jra")
    ap.add_argument("--input", action="append", default=[])
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    daily: list[dict] = []; calendar_rows: list[dict] = []
    if args.input:
        races = collect_files(args.input)
    else:
        days = max(30, min(args.days, 240))
        max_races = max(120, min(args.max_races, 900))
        races, daily, ids = collect_d1_central(args.api_url, days, outdir)
        needed = max(0, max_races - len(races))
        if needed:
            official, calendar_rows = collect_jra_official(days, needed, ids, outdir, args.workers)
            races.extend(official)

    uniq = {r.race_id: r for r in races if r.race_id}
    races = sorted(uniq.values(), key=lambda r: (r.race_date, r.track, r.race_no, r.race_id))
    if len(races) < 35:
        msg = f"中央の有効確定レースが **{len(races)}件**。最低35件必要です。期間またはmax_racesを増やして再実行してください。"
        (outdir / "report.md").write_text("# ARVEXQ v208 中央専用バックテスト\n\n" + msg + "\n", encoding="utf-8")
        (outdir / "report.json").write_text(json.dumps({"version": MODEL_VERSION, "raceCount": len(races), "error": "insufficient JRA sample"}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(msg)
        return 0

    candidate, search = core.optimize(races, max(500, args.iterations), args.seed)
    _, valid, hold = core.split_time(races)
    evalset = hold if hold else valid if valid else races
    promo = core.promotion_decision(evalset, candidate)
    segments = core.segment_report(evalset, candidate, min_n=max(8, min(20, len(evalset)//5)))
    specialized = optimize_segments(races, max(900, args.iterations), args.seed)
    tb = core.ticket_metrics(evalset, None, True)
    tc = core.ticket_metrics(evalset, candidate, False)
    write_report(outdir, races, candidate, search, promo, segments, specialized, tb, tc, daily, calendar_rows)
    print(json.dumps({"races": len(races), "evalRaces": len(evalset), "promotion": promo, "baseline": core.metric_block(evalset, baseline=True), "candidate": core.metric_block(evalset, candidate)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
