#!/usr/bin/env python3
"""Forward scoreboard extensions: calibration, confidence bands,
per-mark records and the honmei-flow per-ticket-type table.

Usage:
  python scripts/arvexq_forward_scoreboard.py \
      [--v1-db var/seals/sealed.sqlite3] \
      [--v8-db var/seals/sealed_shadow_v8.sqlite3] \
      [--late-db var/seals/sealed_shadow_late.sqlite3] \
      [--out-json <path>] [--out-md <path>] \
      [--results-cache <path>] [--no-fetch]

What it adds on top of the headline scoreboard (which reports
logloss / honmei rates): the three reporting shapes the domestic
evidence says a seller must publish to be believed —

(a) Calibration bins: for the honmei's predicted win probability
    and top-3 probability, predicted vs actual in bins. A model
    whose "30%" horses win 20% of the time is over-confident no
    matter what its hit rate says (kensho_ya's finding: calibration
    is what makes or breaks EV use; keiba_model_lab publishes the
    same predicted-vs-actual table).
(b) Confidence bands: races ranked by honmei win probability,
    top 5/10/25/50% bands, model honmei win rate vs the SAME
    races' 1st-favourite win rate. Selection only counts if it
    beats the favourite on the identical race set (charat55's
    warning: subset selection moves the baseline).
(c) Per-mark records (◎○▲△☆ win / top-3 rates) and, for the v1
    lane, the honmei-flow table per ticket type (win, place,
    wide, quinella, exacta, trio, trifecta): hit rate, ROI and
    average points, graded against actual payouts. Tickets are
    regenerated from the day's ingest DB with the frozen lane
    configuration and used ONLY where the regenerated marks match
    the sealed marks exactly (the established scoreboard rule);
    mismatches are counted, never silently included.

Results come from the production API (GET only) and are cached
in a JSON file so reruns are cheap and the graded set is stable.
Only races with a confirmed result are graded; pending races are
counted and reported, never guessed.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.lane_config import LANE_BETA, LANE_WEIGHTS  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.data.sources import API_BASE, BROWSER_UA  # noqa: E402
from rewrite.data.store import Store  # noqa: E402
from rewrite.output.sealing import SealStore  # noqa: E402

KIND_JA = {"win": "単勝", "place": "複勝", "wide": "ワイド",
           "quinella": "馬連", "exacta": "馬単", "trio": "3連複",
           "trifecta": "3連単"}
MARKS = ("◎", "○", "▲", "△", "☆")
BANDS = (0.05, 0.10, 0.25, 0.50)


def fetch_result(race_id: str) -> dict | None:
    url = f"{API_BASE}/api/race/{urllib.parse.quote(race_id, safe='')}"
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = (payload.get("detail") or {}).get("result") or {}
    if result.get("status") != "確定":
        return None
    finishers = [
        {"n": f["horseNumber"], "finish": f.get("finish"),
         "popularity": f.get("popularity")}
        for f in result.get("finishers") or []
        if isinstance(f.get("finish"), (int, float))
    ]
    payouts = {}
    for row in result.get("payouts") or []:
        payouts[(row.get("type"), str(row.get("combination")))] = row.get("amount")
    return {"finishers": finishers, "payouts": payouts}


def sealed_races(path: Path) -> list[dict]:
    if not path.exists():
        return []
    store = SealStore(str(path))
    try:
        out = []
        for row in store.list():
            payload = row["payload"]
            detail = (payload.get("racePayload") or {}).get("detail") or {}
            unified = detail.get("unifiedForecast") or {}
            marks = {}
            probs = {}
            for entry in unified.get("marks") or []:
                marks[entry["horseNumber"]] = entry["markSymbol"]
                probs[entry["horseNumber"]] = (
                    entry.get("winProbability"), entry.get("top3Probability"))
            out.append({
                "race_id": row["race_id"], "model_key": row["model_key"],
                "marks": marks, "probs": probs,
                "honmei": unified.get("honmeiHorseNumber"),
            })
        return out
    finally:
        store.close()


def grade_lane(races: list[dict], results: dict) -> dict:
    graded = []
    for race in races:
        result = results.get(race["race_id"])
        if not result:
            continue
        finish = {f["n"]: f["finish"] for f in result["finishers"]}
        winner = next((n for n, f in finish.items() if f == 1), None)
        top3 = {n for n, f in finish.items() if f <= 3}
        favourite = next(
            (f["n"] for f in result["finishers"] if f["popularity"] == 1),
            None)
        honmei = race["honmei"]
        if honmei is None or honmei not in race["probs"]:
            continue
        p_win, p_top3 = race["probs"][honmei]
        graded.append({
            "race_id": race["race_id"], "honmei": honmei,
            "p_win": p_win, "p_top3": p_top3,
            "won": 1.0 if honmei == winner else 0.0,
            "top3": 1.0 if honmei in top3 else 0.0,
            "fav_won": 1.0 if favourite == winner else 0.0,
            "marks": race["marks"], "finish": finish, "top3_set": top3,
            "winner": winner,
        })
    return graded


def calibration_bins(graded: list[dict], key: str,
                     outcome: str) -> list[dict]:
    bins = defaultdict(list)
    for g in graded:
        p = g[key]
        if p is None:
            continue
        idx = min(int(p * 10), 9)
        bins[idx].append(g[outcome])
    out = []
    for idx in sorted(bins):
        values = bins[idx]
        out.append({
            "bin": f"{idx / 10:.1f}-{idx / 10 + 0.1:.1f}",
            "n": len(values),
            "predicted_mean": round(
                sum(g[key] for g in graded
                    if g[key] is not None
                    and min(int(g[key] * 10), 9) == idx) / len(values), 4),
            "actual_rate": round(sum(values) / len(values), 4),
        })
    return out


def confidence_bands(graded: list[dict]) -> list[dict]:
    if not graded:
        return []
    ranked = sorted(graded, key=lambda g: -(g["p_win"] or 0.0))
    out = []
    for frac in BANDS:
        k = max(1, round(len(ranked) * frac))
        band = ranked[:k]
        out.append({
            "band": f"top{int(frac * 100)}%",
            "races": k,
            "model_win_rate": round(sum(g["won"] for g in band) / k, 4),
            "favourite_win_rate": round(
                sum(g["fav_won"] for g in band) / k, 4),
            "diff_pt": round(
                100 * (sum(g["won"] for g in band)
                       - sum(g["fav_won"] for g in band)) / k, 2),
        })
    return out


def per_mark(graded: list[dict]) -> dict:
    stats = {}
    for mark in MARKS:
        rows = []
        for g in graded:
            for number, symbol in g["marks"].items():
                if symbol == mark:
                    rows.append((number, g))
        if rows:
            stats[mark] = {
                "n": len(rows),
                "win_rate": round(
                    sum(1 for n, g in rows if n == g["winner"]) / len(rows), 4),
                "top3_rate": round(
                    sum(1 for n, g in rows if n in g["top3_set"]) / len(rows), 4),
            }
    return stats


def combo_key(kind: str, selection: tuple, finish: dict) -> str:
    if kind in ("win", "place"):
        return str(selection[0])
    if kind in ("wide", "quinella", "trio"):
        return "-".join(str(n) for n in sorted(selection))
    return "-".join(str(n) for n in selection)  # exacta, trifecta


def honmei_flow(project: Path, races: list[dict],
                results: dict) -> dict:
    """Regenerate v1 tickets per race date and grade every kind."""
    by_date = defaultdict(list)
    sealed_marks = {}
    for race in races:
        by_date[race["race_id"][4:14]].append(race["race_id"])
        sealed_marks[race["race_id"]] = {
            n: s for n, s in race["marks"].items()}
    totals = {kind: {"points": 0, "hits": 0, "return": 0.0, "races": 0}
              for kind in KIND_JA}
    matched = mismatched = 0
    for date, race_ids in sorted(by_date.items()):
        db_path = project / "var" / f"rewrite-{date}.sqlite3"
        if not db_path.exists():
            continue
        store = Store(str(db_path))
        try:
            for race in store.load_races():
                if race.race_id not in race_ids:
                    continue
                result = results.get(race.race_id)
                if not result:
                    continue
                forecast = forecast_race(
                    race, beta=LANE_BETA,
                    weights=LANE_WEIGHTS.get(race.segment.value, {}))
                regen_marks = {r.number: r.mark
                               for r in forecast.runners if r.mark}
                if regen_marks != sealed_marks.get(race.race_id, {}):
                    mismatched += 1
                    continue
                matched += 1
                win_odds = {
                    r.number: r.win_odds.value for r in race.runners
                    if r.win_odds.present
                    and isinstance(r.win_odds.value, (int, float))}
                plan = generate_tickets(
                    forecast, win_odds, calibration_validated=False)
                finish = {f["n"]: f["finish"]
                          for f in result["finishers"]}
                payouts = {(t, c): a for (t, c), a in
                           ((k, v) for k, v in result["payouts"].items())}
                for ticket in plan.probability_tickets:
                    bucket = totals[ticket.kind]
                    bucket["points"] += 1
                    amount = result["payouts"].get(
                        (KIND_JA[ticket.kind],
                         combo_key(ticket.kind, ticket.selection, finish)))
                    if amount is not None:
                        bucket["hits"] += 1
                        bucket["return"] += amount / 100.0
                for kind in totals:
                    pass
                kinds_in_race = {t.kind for t in plan.probability_tickets}
                for kind in kinds_in_race:
                    totals[kind]["races"] += 1
        finally:
            store.close()
    out = {}
    for kind, ja in KIND_JA.items():
        b = totals[kind]
        out[ja] = {
            "races": b["races"], "points": b["points"],
            "avg_points": round(b["points"] / b["races"], 2)
            if b["races"] else None,
            "hits": b["hits"],
            "hit_rate": round(b["hits"] / b["points"], 4)
            if b["points"] else None,
            "roi": round(b["return"] / b["points"], 4)
            if b["points"] else None,
        }
    return {"matched_races": matched, "mismatched_races": mismatched,
            "by_kind": out}


def render_md(report: dict) -> str:
    lines = ["# 前向きスコアボード拡張（校正・自信帯・印別・◎流し券種別）", ""]
    for lane, data in report["lanes"].items():
        lines.append(f"## {lane}（採点 {data['graded']} / 封印 {data['sealed']}）")
        lines.append("")
        lines.append("### 校正（◎勝率: 予測 vs 実績）")
        lines.append("| 帯 | n | 予測平均 | 実績 |")
        lines.append("|---|---|---|---|")
        for b in data["calibration_win"]:
            lines.append(f"| {b['bin']} | {b['n']} | {b['predicted_mean']} | {b['actual_rate']} |")
        lines.append("")
        lines.append("### 校正（◎3着内率: 予測 vs 実績）")
        lines.append("| 帯 | n | 予測平均 | 実績 |")
        lines.append("|---|---|---|---|")
        for b in data["calibration_top3"]:
            lines.append(f"| {b['bin']} | {b['n']} | {b['predicted_mean']} | {b['actual_rate']} |")
        lines.append("")
        lines.append("### 自信帯（◎勝率の高い順・同一レースの1番人気と比較）")
        lines.append("| 帯 | レース数 | モデル◎勝率 | 1番人気勝率 | 差(pt) |")
        lines.append("|---|---|---|---|---|")
        for b in data["confidence_bands"]:
            lines.append(f"| {b['band']} | {b['races']} | {b['model_win_rate']} | {b['favourite_win_rate']} | {b['diff_pt']} |")
        lines.append("")
        lines.append("### 印別成績")
        lines.append("| 印 | n | 勝率 | 3着内率 |")
        lines.append("|---|---|---|---|")
        for mark, s in data["per_mark"].items():
            lines.append(f"| {mark} | {s['n']} | {s['win_rate']} | {s['top3_rate']} |")
        lines.append("")
    flow = report.get("honmei_flow_v1")
    if flow:
        lines.append(f"## ◎流し券種別（本線v1・再生成印一致 {flow['matched_races']} レース / 不一致 {flow['mismatched_races']}）")
        lines.append("| 券種 | レース数 | 点数 | 平均点数 | 的中 | 的中率 | 回収率 |")
        lines.append("|---|---|---|---|---|---|---|")
        for ja, s in flow["by_kind"].items():
            lines.append(f"| {ja} | {s['races']} | {s['points']} | {s['avg_points']} | {s['hits']} | {s['hit_rate']} | {s['roi']} |")
        lines.append("")
    lines.append("注記: 母数が小さいうちは校正ビン・自信帯とも誤差が大きい。"
                 "判定は計画書の母数（同一レース300件〜）に達してから行う。")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-db", default="var/seals/sealed.sqlite3")
    parser.add_argument("--v8-db", default="var/seals/sealed_shadow_v8.sqlite3")
    parser.add_argument("--late-db", default="var/seals/sealed_shadow_late.sqlite3")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--results-cache", required=True)
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args()

    project = Path(__file__).resolve().parent.parent
    cache_path = Path(args.results_cache)
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    lanes = {}
    all_races = {}
    for name, db in (("v1", args.v1_db), ("v8", args.v8_db),
                     ("late", args.late_db)):
        races = sealed_races(project / db)
        if races:
            lanes[name] = races
            all_races.update({r["race_id"]: r for r in races})

    if not args.no_fetch:
        for race_id in sorted(all_races):
            if race_id in cache:
                continue
            try:
                result = fetch_result(race_id)
            except Exception:
                continue
            if result is not None:
                # payouts dict keys are tuples in memory; JSON needs str
                cache[race_id] = {
                    "finishers": result["finishers"],
                    "payouts": {f"{t}|{c}": a
                                for (t, c), a in result["payouts"].items()},
                }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    results = {}
    for race_id, entry in cache.items():
        results[race_id] = {
            "finishers": entry["finishers"],
            "payouts": {tuple(k.split("|", 1)): v
                        for k, v in entry["payouts"].items()},
        }

    report = {"lanes": {}}
    for name, races in lanes.items():
        graded = grade_lane(races, results)
        report["lanes"][name] = {
            "sealed": len(races), "graded": len(graded),
            "calibration_win": calibration_bins(graded, "p_win", "won"),
            "calibration_top3": calibration_bins(graded, "p_top3", "top3"),
            "confidence_bands": confidence_bands(graded),
            "per_mark": per_mark(graded),
        }
    if "v1" in lanes:
        report["honmei_flow_v1"] = honmei_flow(
            project, lanes["v1"], results)

    Path(args.out_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(args.out_md).write_text(render_md(report), encoding="utf-8")
    print(json.dumps({
        "lanes": {k: {"sealed": v["sealed"], "graded": v["graded"]}
                  for k, v in report["lanes"].items()},
        "flow_matched": (report.get("honmei_flow_v1") or {}).get(
            "matched_races"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
