"""Shared machinery for the NIDONE-factor research program.

Everything here is research-only: it reads the corpus / verify base /
prior record sets and produces candidate probabilities by adjusting
the v9b calibrated base at the probability level (the same frozen
base the v38 lane used), then applying production's exact temperature
history and market blend rule.  Production code is imported read-only
(shadow_v9 blend/market helpers, forecast marks, PL marginals).
"""
from __future__ import annotations

import bisect
import json
import math
import pickle
import random
import sqlite3
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
SCRATCH = PROJECT / "var" / "scratch" / "nidone-factors-20261109"
CORPUS_PATH = SCRATCH / "corpus.sqlite3"
VERIFY_BASE = PROJECT / "var" / "seals" / "verify_base.sqlite3"

import sys
sys.path.insert(0, str(PROJECT))
from rewrite.analysis.forecast import FLOOR_FRACTION, _assign_marks  # noqa: E402
from rewrite.analysis.shadow_v8 import BETAS, WEIGHTS  # noqa: E402
from rewrite.analysis.shadow_v9 import (  # noqa: E402
    TEMPERATURE, blend_probs, market_probs, temperature_probs,
    usable_market)
from rewrite.safety.probability import distribution, marginals  # noqa: E402

ELO_FEATURES = ("elo", "elo_rel", "elo_evidence")
MARK_RANK = {"◎": 1, "○": 2, "▲": 3, "△": 4, "☆": 5}
LOGLOSS_FLOOR = 1e-12


# ------------------------------------------------------------------
# corpus access
# ------------------------------------------------------------------
def corpus() -> sqlite3.Connection:
    return sqlite3.connect(CORPUS_PATH)


class History:
    """Per-horse race history + per-race fields from the corpus."""

    def __init__(self, db: sqlite3.Connection):
        self.by_key: dict[tuple, list] = defaultdict(list)
        self.by_horse: dict[str, list] = defaultdict(list)
        for nk, rdate, track, rnum, fin, fsize, _m, tb in db.execute(
                "SELECT natkey, run_date, track, race_number, finish,"
                " field_size, margin_seconds, time_behind FROM history"
                " WHERE finish IS NOT NULL AND finish > 0"):
            row = (rdate, track, int(rnum), int(fin), fsize, tb)
            self.by_key[(rdate, track, int(rnum))].append((nk, int(fin), fsize, tb))
            self.by_horse[nk].append(row)
        self._dates: dict[str, list] = {}
        for nk, rows in self.by_horse.items():
            rows.sort(key=lambda r: r[0])
            self._dates[nk] = [r[0] for r in rows]

    def subsequent(self, natkey: str, after: str, before: str):
        """History rows of a horse with after < date < before."""
        rows = self.by_horse.get(natkey)
        if not rows:
            return []
        dates = self._dates[natkey]
        lo = bisect.bisect_right(dates, after)
        hi = bisect.bisect_left(dates, before)
        return rows[lo:hi]


# ------------------------------------------------------------------
# base probabilities from prior record sets (regeneration basis)
# ------------------------------------------------------------------
def record_norm(record: dict) -> dict:
    """{number: {feature: value}} minmax norms from either record set."""
    if "norm" in record:  # nar-rebuild records
        return record["norm"]["mm"]
    return record["norm_mm"]  # jra-structural records


def base_strengths(record: dict, weights: dict, beta: float):
    """Replica of forecast_race_v8's scoring path (as verified by the
    NAR rebuild's check_replica): returns (status, strengths)."""
    norm = record_norm(record)
    scores: dict[int, float] = {}
    for n in record["numbers"]:
        if record["evidence_runs"].get(n, 0) == 0:
            continue
        feats = norm.get(n) or {}
        available = {k: feats[k] for k in weights if k in feats}
        if len(available) < 3:
            continue
        total_w = sum(weights[k] for k in available)
        scores[n] = round(
            sum(available[k] * weights[k] for k in available) / total_w, 4)
    if len(scores) < 3:
        return "insufficient-scored-runners", {}
    mean_score = sum(scores.values()) / len(scores)
    strengths = {n: math.exp(beta * (s - mean_score))
                 * record["pace_factor"].get(n, 1.0)
                 for n, s in scores.items()}
    floor = FLOOR_FRACTION * min(strengths.values())
    for n in record["numbers"]:
        if n not in strengths:
            strengths[n] = floor
    return "ok", strengths


def pcal_from_strengths(strengths: dict) -> dict:
    total = sum(strengths.values())
    base = {n: s / total for n, s in strengths.items()}
    return temperature_probs(base, TEMPERATURE)


def weights_without_elo(segment: str) -> dict:
    return {k: v for k, v in WEIGHTS[segment].items()
            if k not in ELO_FEATURES}


# ------------------------------------------------------------------
# candidate construction
# ------------------------------------------------------------------
def zscore(features: dict, keys: list) -> dict:
    """features: {number: {key: value|None}} -> {number: {key: z}}.

    Within-race standardization over runners carrying the feature;
    missing stays exactly 0 (the registered neutral)."""
    out = {n: {} for n in features}
    for k in keys:
        vals = [f[k] for f in features.values() if f.get(k) is not None]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            sd = math.sqrt(var)
        else:
            mean, sd = 0.0, 0.0
        for n, f in features.items():
            v = f.get(k)
            out[n][k] = ((v - mean) / sd) if (v is not None and sd > 1e-9) else 0.0
    return out


def candidate_probs(p_cal: dict, odds: dict, z: dict, gamma: dict):
    """final = blend(normalize(p_cal * exp(gamma.z)), market) with
    production's usable-market rule; returns (probs, marks)."""
    adj = {}
    for n, p in p_cal.items():
        g = sum(gamma.get(k, 0.0) * z.get(n, {}).get(k, 0.0) for k in gamma)
        adj[n] = p * math.exp(g)
    total = sum(adj.values())
    if total <= 0:
        return None, {}
    q = {n: v / total for n, v in adj.items()}
    if odds and usable_market(odds, q):
        final = blend_probs(q, market_probs(odds, q))
    else:
        final = q
    probs = marginals(distribution(dict(final)))
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranked, probs)
    win = {n: probs[n][0] for n in probs}
    top3 = {n: probs[n][2] for n in probs}
    return (win, top3), marks


def plain_probs(p_cal: dict, odds: dict):
    """The unadjusted arm on the same basis (gamma = 0)."""
    return candidate_probs(p_cal, odds, {}, {})


# ------------------------------------------------------------------
# metrics
# ------------------------------------------------------------------
def marks_of(probs_win: dict, probs_top3: dict) -> dict:
    ranked = sorted(probs_win, key=lambda n: (-probs_win[n], -probs_top3[n], n))
    fake = {n: (probs_win[n], 0.0, probs_top3[n]) for n in probs_win}
    return _assign_marks(ranked, fake)


def ticket_hit(marks: dict, finish: dict, win_leg: set) -> bool:
    rank = {n: MARK_RANK[m] for n, m in marks.items() if m in MARK_RANK}
    by_finish = {f: n for n, f in finish.items()}
    if not all(f in by_finish for f in (1, 2, 3)):
        return False
    w, s, t = by_finish[1], by_finish[2], by_finish[3]
    return (rank.get(w) in win_leg and rank.get(s) in (1, 2, 3, 4, 5)
            and rank.get(t) in (1, 2, 3, 4, 5))


def race_metrics(probs: dict, marks: dict, finish: dict, winner: int,
                 tri: float | None) -> dict:
    honmei = next((n for n, m in marks.items() if m == "◎"), None)
    ranked = sorted(probs, key=lambda n: (-probs[n], n))
    wrank = ranked.index(winner) + 1 if winner in probs else None
    ll = -math.log(max(probs.get(winner, 0.0), LOGLOSS_FLOOR))
    brier = sum((p - (1.0 if n == winner else 0.0)) ** 2
                for n, p in probs.items())
    return {
        "honmei_win": 1.0 if honmei == winner else 0.0,
        "honmei_top3": 1.0 if finish.get(honmei, 99) <= 3 else 0.0,
        "winner_in_marks": 1.0 if winner in marks else 0.0,
        "winner_rank": wrank,
        "logloss": ll,
        "brier": brier,
        "b36_hit": ticket_hit(marks, finish, {1, 2, 3}),
        "r24_hit": ticket_hit(marks, finish, {1, 2}),
        "tri": tri,
    }


def cluster_bootstrap_ci(rows: list, reps: int = 500,
                         seed: int = 20261109):
    """Day-cluster bootstrap CI of the mean of (race_date, diff) rows."""
    by_date: dict[str, list] = defaultdict(list)
    for d, v in rows:
        by_date[d].append(v)
    dates = sorted(by_date)
    if len(dates) < 2 or not rows:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(reps):
        tot, cnt = 0.0, 0
        for _ in range(len(dates)):
            d = dates[rng.randrange(len(dates))]
            for v in by_date[d]:
                tot += v
                cnt += 1
        means.append(tot / cnt if cnt else 0.0)
    means.sort()
    point = sum(v for _, v in rows) / len(rows)
    return {"mean": round(point, 4),
            "ci95": [round(means[int(0.025 * reps)], 4),
                     round(means[min(reps - 1, int(0.975 * reps))], 4)]}


def paired_block(pairs: list) -> dict:
    """pairs: list of dicts with date, base/cand race_metrics and
    favourite_win.  Returns the registered judgement block."""
    n = len(pairs)
    out = {"pairs": n}
    if not n:
        return out
    for mk in ("honmei_win", "honmei_top3", "winner_in_marks"):
        diffs = [(p["date"], p["cand"][mk] - p["base"][mk]) for p in pairs]
        out[f"{mk}_diff"] = cluster_bootstrap_ci(diffs)
        out[f"{mk}_rate"] = {
            "base": round(sum(p["base"][mk] for p in pairs) / n, 4),
            "cand": round(sum(p["cand"][mk] for p in pairs) / n, 4)}
    for mk in ("logloss", "brier"):
        diffs = [(p["date"], p["cand"][mk] - p["base"][mk]) for p in pairs]
        out[f"{mk}_diff"] = cluster_bootstrap_ci(diffs)
        out[mk] = {"base": round(sum(p["base"][mk] for p in pairs) / n, 4),
                   "cand": round(sum(p["cand"][mk] for p in pairs) / n, 4)}
    wr = [(p["date"], (p["cand"]["winner_rank"] or 99)
           - (p["base"]["winner_rank"] or 99)) for p in pairs
          if p["cand"]["winner_rank"] and p["base"]["winner_rank"]]
    out["winner_rank_diff"] = cluster_bootstrap_ci(wr)
    out["winner_rank"] = {
        "base": round(sum(p["base"]["winner_rank"] for p in pairs
                          if p["base"]["winner_rank"]) /
                      max(1, sum(1 for p in pairs if p["base"]["winner_rank"])), 3),
        "cand": round(sum(p["cand"]["winner_rank"] for p in pairs
                          if p["cand"]["winner_rank"]) /
                      max(1, sum(1 for p in pairs if p["cand"]["winner_rank"])), 3)}
    out["honmei_wins"] = {"base": int(sum(p["base"]["honmei_win"] for p in pairs)),
                          "cand": int(sum(p["cand"]["honmei_win"] for p in pairs)),
                          "favourite": int(sum(p["favourite_win"] for p in pairs))}
    roi_rows = [p for p in pairs if p["cand"].get("tri") is not None]
    out["roi_pairs"] = len(roi_rows)
    for form, pts in (("b36", 36), ("r24", 24)):
        for arm in ("base", "cand"):
            hits = [p for p in roi_rows if p[arm][f"{form}_hit"]]
            ret = sum(p[arm]["tri"] for p in hits)
            roi = ret / (pts * 100 * len(roi_rows)) if roi_rows else None
            out[f"{form}_{arm}"] = {"hits": len(hits),
                                    "roi": round(roi, 4) if roi is not None else None}
            if hits:
                big = max(hits, key=lambda p: p[arm]["tri"])
                ret_ex = ret - big[arm]["tri"]
                out[f"{form}_{arm}"]["roi_ex_max"] = round(
                    ret_ex / (pts * 100 * len(roi_rows)), 4)
    return out


# ------------------------------------------------------------------
# verify base (primary window)
# ------------------------------------------------------------------
def load_primary_window():
    """Production final forms + inverted bases for 2026-11-04..08."""
    vb = sqlite3.connect(VERIFY_BASE)
    bases = {}
    for race_id, active, p_cal, odds, stored, marks in vb.execute(
            "SELECT race_id, active, p_cal, publish_odds, stored_probs,"
            " stored_marks FROM ability_bases WHERE ok = 1"):
        bases[race_id] = {
            "active": json.loads(active),
            "p_cal": {int(k): v for k, v in json.loads(p_cal).items()},
            "odds": {int(k): v for k, v in json.loads(odds).items()},
            "stored_probs": {int(k): v for k, v in json.loads(stored).items()},
            "stored_marks": {int(k): v for k, v in json.loads(marks).items()},
        }
    results = {}
    for race_id, finish, payouts in vb.execute(
            "SELECT race_id, finish, payouts_tri FROM results"):
        fin = {int(k): v for k, v in json.loads(finish).items()} if finish else {}
        tri = None
        if payouts:
            pj = json.loads(payouts)
            if pj:
                tri = next(iter(pj.values()))
        if fin:
            winner = next((n for n, f in fin.items() if f == 1), None)
            results[race_id] = {"finish": fin, "winner": winner, "tri": tri}
    vb.close()
    return bases, results


def load_records():
    """The NAR-rebuild + JRA-structural record sets."""
    nar = pickle.loads(
        (PROJECT / "var/scratch/nar-rebuild-20261109/records.pkl").read_bytes())
    jra = pickle.loads(
        (PROJECT / "var/scratch/jra-structural-20261109/records_fit.pkl").read_bytes())
    jra += pickle.loads(
        (PROJECT / "var/scratch/jra-structural-20261109/records_judge.pkl").read_bytes())
    return nar, jra
