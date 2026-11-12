"""Research-only evaluation of the F1 evidence-decay challenger.

Same-race A/B on settled production races from the v9b era.

Data sources (two, joined by race_id):

- Sealed forecasts: the repository's saved snapshots
  (``arvexq/ui/static/saved-snapshots/*.json``, gzip envelopes of the
  publish-time details). 415 carry a v9b unifiedForecast and every
  one verifies under ``unified_product.verified``. This matters
  because the production API read-back no longer returns the
  unifiedForecast block for 2026-11-04..07 details at all.
- Results (labels only): the production API detail's ``result``.
  Where no snapshot exists (2026-11-12), the API detail's own sealed
  forecast is used when it verifies.

Arms:

- ``sealed``   : production v9b probabilities exactly as sealed
                 (reference truth — computed at publish time WITH the
                 v8 extras lane).
- ``base``     : production code recomputed from the sealed detail
                 payload (``normalize_race`` -> ``forecast_race_v8``
                 -> ``postprocess_forecast(arm="v9b")``), with
                 ``extras={}`` (the extras export file is generated
                 outside this repository — audit F9 — and is not
                 reachable for past dates; both recomputed arms share
                 this limit, so the A/B isolates the decay change).
- ``runs-k2`` / ``runs-k4`` / ``cov-k2`` / ``cov-k4``:
                 the challenger (``f1_evidence_decay``) put through
                 the identical v9b post-processing.

Eligibility mirrors the strict audit's spirit: banei excluded, the
sealed forecast must verify, the result must be final with a
finisher roster identical to the sealed roster and exactly one
winner. Results are labels only — never features; past runs dated
on/after the race date are rejected by ``normalize_race`` itself.

This is a DEVELOPMENT evaluation on already-raced dates (the same
period earlier diagnostics used), not an independent sealed test.
Metrics: honmei win rate, honmei top-3 rate, winner-in-top-3 rate,
NDCG@3, log loss, Brier (win). Differences are challenger minus base
per race, with date-cluster bootstrap 95% CIs (dates resampled with
replacement; JRA has only two race days in the window, so its CIs
are coarse by construction).

Usage:
    python3 -m arvexq.research.f1_evidence_decay_eval \
        --compute --dates 2026-11-04..2026-11-12 \
        --cache DIR --races-out races.jsonl
    python3 -m arvexq.research.f1_evidence_decay_eval \
        --report --races-out races.jsonl --out report.json
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import gzip
import json
from math import log, log2
from pathlib import Path
import random
import sys
import urllib.parse
import urllib.request

API_BASE = "https://kraiz-api.4b89h4fydd.workers.dev"
EPS = 1e-12
SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / \
    "arvexq" / "ui" / "static" / "saved-snapshots"


def _get(path: str, cache_file: Path | None) -> dict:
    if cache_file is not None and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        API_BASE + path,
        headers={"User-Agent": "arvexq-f1-research", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(payload, ensure_ascii=False),
                              encoding="utf-8")
    return payload


def load_snapshot_forecasts() -> dict[str, dict]:
    """race_id -> publish-time detail for every snapshot whose sealed
    v9b forecast verifies."""
    from arvexq.prediction.unified_product import verified

    out: dict[str, dict] = {}
    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
            detail = json.loads(gzip.decompress(
                base64.b64decode(env["gzipBase64"])))
        except Exception:
            continue
        uf = detail.get("unifiedForecast")
        if not isinstance(uf, dict):
            continue
        if "v9b" not in str(uf.get("modelVersion") or ""):
            continue
        race_id = detail.get("id") or uf.get("raceId")
        if not race_id or race_id in out:
            continue
        if verified(detail) is None:
            continue
        out[race_id] = detail
    return out


def race_metrics(probs: dict[int, float], honmei: int,
                 finish: dict[int, int]) -> dict[str, float]:
    winner = min(finish, key=lambda n: finish[n])
    ranked = sorted(probs, key=lambda n: (-probs[n], n))
    gains = {n: max(0, 4 - finish[n]) for n in finish}

    def dcg(order):
        return sum(gains[n] / log2(i + 2) for i, n in enumerate(order[:3]))

    ideal = sorted(gains, key=lambda n: -gains[n])
    idcg = dcg(ideal)
    return {
        "honmei_win": 1.0 if finish[honmei] == 1 else 0.0,
        "honmei_top3": 1.0 if finish[honmei] <= 3 else 0.0,
        "winner_top3": 1.0 if ranked.index(winner) < 3 else 0.0,
        "ndcg3": dcg(ranked) / idcg if idcg > 0 else 0.0,
        "logloss": -log(max(probs[winner], EPS)),
        "brier": sum((p - (1.0 if n == winner else 0.0)) ** 2
                     for n, p in probs.items()),
    }


METRIC_KEYS = ("honmei_win", "honmei_top3", "winner_top3",
               "ndcg3", "logloss", "brier")


def compute(args) -> int:
    from arvexq.ingest.full_snapshot_codec import unpack_detail
    from arvexq.prediction.unified_product import verified
    from arvexq.research.f1_evidence_decay import (
        CANDIDATES, forecast_race_v8_decay)
    from rewrite.analysis.ability import extract_features
    from rewrite.analysis.shadow_v8 import forecast_race_v8
    from rewrite.analysis.shadow_v9 import postprocess_forecast
    from rewrite.data.normalize import normalize_race

    snapshots = load_snapshot_forecasts()
    print(f"snapshot sealed v9b forecasts: {len(snapshots)}", file=sys.stderr)

    races_out = Path(args.races_out)
    done: set[str] = set()
    if races_out.exists():
        for line in races_out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["race_id"])
    print(f"already computed: {len(done)}", file=sys.stderr)

    from datetime import date as _date, timedelta
    start, end = args.dates.split("..")
    day = _date.fromisoformat(start)
    last = _date.fromisoformat(end)
    dates = []
    while day <= last:
        dates.append(day.isoformat())
        day += timedelta(days=1)

    cache_root = Path(args.cache) if args.cache else None
    excluded: dict[str, int] = defaultdict(int)
    fout = races_out.open("a", encoding="utf-8")

    for date in dates:
        listing = _get(f"/api/races?date={date}",
                       cache_root / date / "_listing.json" if cache_root else None)
        summaries = {}
        for s in listing.get("races") or []:
            rid = s.get("race_id") or s.get("id")
            if rid:
                summaries[str(rid)] = s
        snap_today = {rid: d for rid, d in snapshots.items()
                      if str(d.get("date")) == date}
        candidates = sorted(set(summaries) | set(snap_today))
        for race_id in candidates:
            if race_id in done:
                continue
            if "帯広" in race_id:
                excluded["banei"] += 1
                continue
            raw = _get("/api/race/" + urllib.parse.quote(race_id, safe=""),
                       cache_root / date / f"{race_id}.json" if cache_root else None)
            api_detail = unpack_detail(raw.get("detail") or {})
            if race_id in snap_today:
                detail = snap_today[race_id]
                source = "snapshot"
            else:
                detail = api_detail
                source = "api"
            uf = detail.get("unifiedForecast")
            if not isinstance(uf, dict) or "v9b" not in str(uf.get("modelVersion") or ""):
                excluded["no-v9b-forecast"] += 1
                continue
            if source == "api" and verified(detail) is None:
                excluded["receipt-unverified"] += 1
                continue
            result = api_detail.get("result") or {}
            finish = {}
            for f in result.get("finishers") or []:
                if isinstance(f, dict) and isinstance(f.get("finish"), int):
                    finish[int(f["horseNumber"])] = int(f["finish"])
            roster = {int(r["horseNumber"]) for r in uf.get("roster") or []
                      if isinstance(r, dict) and r.get("horseNumber") is not None}
            if result.get("status") != "確定" or not finish:
                excluded["result-not-final"] += 1
                continue
            if set(finish) != roster:
                excluded["roster-result-mismatch"] += 1
                continue
            if sum(1 for v in finish.values() if v == 1) != 1:
                excluded["dead-heat-or-no-winner"] += 1
                continue
            summary = summaries.get(race_id) or {
                "race_id": race_id, "id": race_id, "date": date,
                "track": detail.get("track"),
                "race_number": detail.get("raceNumber"),
            }
            try:
                race = normalize_race(summary, detail,
                                      source="production-api-readback")
            except Exception:
                excluded["normalize-error"] += 1
                continue
            segment = race.segment.value
            if segment not in ("jra_flat", "nar"):
                excluded[f"segment-{segment}"] += 1
                continue
            base_fc = forecast_race_v8(race, {})
            if base_fc.status != "ok":
                excluded["v8-not-ok"] += 1
                continue
            win_odds = {
                r.number: r.win_odds.value
                for r in race.runners
                if r.win_odds.present
                and isinstance(r.win_odds.value, (int, float))
            }
            sealed_probs = {}
            for m in uf.get("diagnosis") or []:
                if isinstance(m, dict) and m.get("winProbability") is not None:
                    sealed_probs[int(m["horseNumber"])] = float(m["winProbability"])
            if set(sealed_probs) != roster:
                for m in uf.get("marks") or []:
                    if isinstance(m, dict) and m.get("winProbability") is not None:
                        sealed_probs.setdefault(
                            int(m["horseNumber"]), float(m["winProbability"]))
            if set(sealed_probs) != roster:
                excluded["sealed-probs-incomplete"] += 1
                continue

            def arm_metrics(fc, honmei_override=None):
                pp, _info = postprocess_forecast(fc, arm="v9b",
                                                 win_odds=win_odds)
                probs = {r.number: r.p_win for r in pp.runners
                         if r.p_win is not None}
                honmei = honmei_override
                if honmei is None:
                    marked = [r.number for r in pp.runners if r.mark == "◎"]
                    honmei = marked[0] if marked else max(
                        probs, key=lambda n: (probs[n], -n))
                return race_metrics(probs, honmei, finish), honmei

            entry: dict = {"race_id": race_id, "date": date,
                           "segment": segment, "source": source,
                           "arms": {}}
            sealed_honmei = uf.get("honmeiHorseNumber")
            if sealed_honmei is None:
                sealed_honmei = max(sealed_probs,
                                    key=lambda n: (sealed_probs[n], -n))
            entry["arms"]["sealed"] = race_metrics(
                sealed_probs, int(sealed_honmei), finish)
            base_metrics, base_honmei = arm_metrics(base_fc)
            entry["arms"]["base"] = base_metrics
            feats = {r.number: extract_features(race, r)
                     for r in race.active_runners}
            entry["base_honmei_evidence_runs"] = (
                feats[base_honmei].evidence_runs if base_honmei in feats else None)
            for name, cfg in CANDIDATES.items():
                fc = forecast_race_v8_decay(race, {}, **cfg)
                if fc.status != "ok":
                    entry["arms"][name] = None
                    continue
                m, honmei = arm_metrics(fc)
                entry["arms"][name] = m
                entry[f"{name}_honmei_changed"] = honmei != base_honmei
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
            fout.flush()
            done.add(race_id)
        print(f"{date}: cumulative eligible {len(done)}; "
              f"excluded so far {dict(excluded)}", file=sys.stderr)
    fout.close()
    print(json.dumps({"eligible_total": len(done),
                      "excluded": dict(excluded)}, ensure_ascii=False))
    return 0


def cluster_bootstrap_ci(diffs_by_date: dict[str, list[float]],
                         reps: int = 2000, seed: int = 20261112):
    dates = sorted(diffs_by_date)
    if not dates:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        vals: list[float] = []
        for _ in dates:
            vals.extend(diffs_by_date[rng.choice(dates)])
        if vals:
            means.append(sum(vals) / len(vals))
    means.sort()
    return (means[int(0.025 * reps)], means[int(0.975 * reps)])


def report(args) -> int:
    from arvexq.research.f1_evidence_decay import CANDIDATES
    arms = ["sealed", "base", *CANDIDATES]
    per_race = [json.loads(line)
                for line in Path(args.races_out).read_text(
                    encoding="utf-8").splitlines() if line.strip()]

    def aggregate(rows):
        out = {}
        for arm in arms:
            vals = [r["arms"][arm] for r in rows if r["arms"].get(arm)]
            if not vals:
                continue
            out[arm] = {k: sum(v[k] for v in vals) / len(vals)
                        for k in METRIC_KEYS}
            out[arm]["races"] = len(vals)
        return out

    def diffs(rows, arm):
        by_date: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list))
        usable = [r for r in rows if r["arms"].get(arm) and r["arms"].get("base")]
        point = {}
        for k in METRIC_KEYS:
            ds = [r["arms"][arm][k] - r["arms"]["base"][k] for r in usable]
            point[k] = sum(ds) / len(ds) if ds else None
            for r in usable:
                by_date[k][r["date"]].append(
                    r["arms"][arm][k] - r["arms"]["base"][k])
        ci = {k: cluster_bootstrap_ci(by_date[k]) for k in METRIC_KEYS}
        return point, ci, len(usable)

    report_doc: dict = {
        "eligible_races": len(per_race),
        "by_source": dict(Counter(r["source"] for r in per_race)),
        "by_date": dict(Counter(r["date"] for r in per_race)),
        "segments": {},
    }
    for segment in ("nar", "jra_flat", "ALL"):
        rows = per_race if segment == "ALL" else [
            r for r in per_race if r["segment"] == segment]
        if not rows:
            continue
        seg_report = {"races": len(rows), "aggregate": aggregate(rows),
                      "challenger_minus_base": {}}
        for name in CANDIDATES:
            point, ci, n = diffs(rows, name)
            seg_report["challenger_minus_base"][name] = {
                "races": n, "mean_diff": point, "ci95_date_cluster": ci}
        report_doc["segments"][segment] = seg_report

    thin = [r for r in per_race
            if (r["base_honmei_evidence_runs"] or 99) <= 2]
    report_doc["thin_evidence_honmei"] = {
        "races": len(thin),
        "base_honmei_win_rate": (
            sum(r["arms"]["base"]["honmei_win"] for r in thin) / len(thin)
            if thin else None),
        "challenger_honmei_win_rate": {
            name: (sum(r["arms"][name]["honmei_win"] for r in thin
                       if r["arms"].get(name)) /
                   max(1, sum(1 for r in thin if r["arms"].get(name))))
            for name in CANDIDATES},
    }
    for name in CANDIDATES:
        changed = [r for r in per_race if r.get(f"{name}_honmei_changed")]
        report_doc.setdefault("honmei_change_rate", {})[name] = (
            len(changed) / len(per_race) if per_race else None)

    text = json.dumps(report_doc, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compute", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--dates", default="2026-11-04..2026-11-12")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--races-out", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    if args.compute:
        return compute(args)
    return report(args)


if __name__ == "__main__":
    raise SystemExit(main())
