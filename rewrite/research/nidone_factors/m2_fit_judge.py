"""M2 fit + judgement (preregistration sections 2, 5, 8).

Main comparison: FIXED gamma vs career-DECAY gamma
(1 / (1 + career_starts/4)) applied per runner.  The 15 group
statistics enter gamma; the group start counts are kept for
reporting only.  NAR: pool fit, primary judgement vs the production
final form, consistency window A vs regeneration, segment breakdown.
JRA: pedigree exists only for the live era (no pool fit material),
so the box is reported as not-yet-judgeable with coverage evidence.
"""
from __future__ import annotations

import csv
import json
import math
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from rewrite.analysis.shadow_v8 import BETAS, WEIGHTS  # noqa: E402
from rewrite.analysis.shadow_v9 import (  # noqa: E402
    blend_probs, market_probs, usable_market)

STAT_FEATURES = ([f"{g}_{s}" for g in
                  ("sire", "sire_turf", "sire_dirt", "damsire", "dam")
                  for s in ("win", "top3", "pctn")])
SEG_OF_BOX = {"nar": "nar", "jra": "jra_flat"}


def final_win_probs(p_cal, odds, z, gamma):
    adj = {}
    for n, p in p_cal.items():
        g = sum(gamma.get(k, 0.0) * z.get(n, {}).get(k, 0.0) for k in gamma)
        adj[n] = p * math.exp(g)
    total = sum(adj.values())
    if total <= 0:
        return None
    q = {n: v / total for n, v in adj.items()}
    if odds and usable_market(odds, q):
        return blend_probs(q, market_probs(odds, q))
    return q


def prepare(records, feats, segment):
    out = []
    weights = WEIGHTS[segment]
    beta = BETAS[segment]
    for rec in records:
        if rec["segment"] != segment:
            continue
        status, strengths = common.base_strengths(rec, weights, beta)
        if status != "ok":
            continue
        p_cal = common.pcal_from_strengths(strengths)
        f = feats.get(rec["race_id"], {})
        raw = {n: f.get(n, {}) for n in p_cal}
        z_fixed = common.zscore(raw, STAT_FEATURES)
        z_decay = {}
        for n, zz in z_fixed.items():
            starts = raw[n].get("career_starts") or 0
            d = 1.0 / (1.0 + starts / 4.0)
            z_decay[n] = {k: v * d for k, v in zz.items()}
        out.append({
            "race_id": rec["race_id"], "date": rec["date"],
            "p_cal": p_cal, "odds": rec.get("win_odds") or {},
            "z_fixed": z_fixed, "z_decay": z_decay, "raw": raw,
            "winner": rec.get("winner"),
            "finish": rec.get("finishers") or {},
            "tri": rec.get("tri_payout"),
        })
    return out


def fit_gamma(bundles, zkey, label):
    cache_path = common.SCRATCH / "m2_gamma_cache.json"
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if label in cache:
        print(f"fit[{label}] loaded from cache", flush=True)
        c = cache[label]
        return c["gamma"], c["ll"], c["n"]
    fit = [b for b in bundles if b["winner"] in b["p_cal"]]
    gamma = {k: 0.0 for k in STAT_FEATURES}

    def objective(g):
        tot = 0.0
        for b in fit:
            probs = final_win_probs(b["p_cal"], b["odds"], b[zkey], g)
            if probs is None:
                return math.inf
            tot += -math.log(max(probs.get(b["winner"], 0.0), 1e-12))
        return tot / len(fit)

    cur = objective(gamma)
    base_ll = cur
    for step in (0.4, 0.2, 0.1, 0.05, 0.025, 0.01):
        improved = True
        while improved:
            improved = False
            for k in STAT_FEATURES:
                for delta in (step, -step):
                    trial = dict(gamma)
                    trial[k] = max(-2.0, min(2.0, trial[k] + delta))
                    if trial[k] == gamma[k]:
                        continue
                    val = objective(trial)
                    if val < cur - 1e-7:
                        gamma, cur = trial, val
                        improved = True
        print(f"fit[{label}] step done ll={cur:.4f}", flush=True)
    cache[label] = {"gamma": gamma, "ll": cur, "n": len(fit),
                    "base_ll": base_ll}
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    return gamma, cur, len(fit)


def judge_detail(bundles, gamma, zkey, base_mode, prod=None):
    """Per-race detail rows (for headline blocks AND segments)."""
    rows = []
    for b in bundles:
        rid = b["race_id"]
        if b["winner"] is None:
            continue
        got = common.candidate_probs(b["p_cal"], b["odds"], b[zkey], gamma)
        if got is None:
            continue
        (cwin, ctop3), cmarks = got
        cand_m = common.race_metrics(cwin, cmarks, b["finish"],
                                     b["winner"], b["tri"])
        if base_mode == "production":
            pb = prod[rid]
            base_probs, base_marks = pb["stored_probs"], pb["stored_marks"]
            base_m = common.race_metrics(base_probs, base_marks,
                                         b["finish"], b["winner"], b["tri"])
            odds = pb["odds"]
        else:
            got0 = common.plain_probs(b["p_cal"], b["odds"])
            if got0 is None:
                continue
            (bwin, btop3), bmarks = got0
            base_probs, base_marks = bwin, bmarks
            base_m = common.race_metrics(bwin, bmarks, b["finish"],
                                         b["winner"], b["tri"])
            odds = b["odds"]
        fav = min(odds, key=lambda n: (odds[n], n)) if odds else None
        rows.append({
            "race_id": rid, "date": b["date"], "winner": b["winner"],
            "base": base_m, "cand": cand_m,
            "favourite_win": 1.0 if fav == b["winner"] else 0.0,
            "base_honmei": next((n for n, m in base_marks.items()
                                 if m == "◎"), None),
            "cand_honmei": next((n for n, m in cmarks.items()
                                 if m == "◎"), None),
            "base_winner_prob": base_probs.get(b["winner"], 0.0),
            "cand_winner_prob": cwin.get(b["winner"], 0.0),
            "raw": b["raw"], "tri": b["tri"],
        })
    return rows


def to_pairs(rows):
    return [{"date": r["date"], "base": r["base"], "cand": r["cand"],
             "favourite_win": r["favourite_win"], "race_id": r["race_id"]}
            for r in rows]


def career_bucket(starts):
    if starts == 0:
        return "career_0"
    if starts <= 3:
        return "career_1_3"
    if starts <= 8:
        return "career_4_8"
    return "career_9plus"


def segment_report(rows):
    """Descriptive per-segment paired diffs (registered reporting).

    For each segment: races whose BASE honmei is in the segment
    (honmei diffs) and races whose WINNER is in the segment
    (winner-probability / rank diffs)."""
    segs = ["career_0", "career_1_3", "career_4_8", "career_9plus",
            "first_surface", "distance_change", "transfer"]

    def tags(raw_entry):
        out = {career_bucket(raw_entry.get("career_starts") or 0)}
        if raw_entry.get("first_surface"):
            out.add("first_surface")
        if raw_entry.get("distance_change"):
            out.add("distance_change")
        if raw_entry.get("transfer"):
            out.add("transfer")
        return out

    report = {}
    for seg in segs:
        h_rows = [r for r in rows
                  if r["base_honmei"] in r["raw"]
                  and seg in tags(r["raw"][r["base_honmei"]])]
        w_rows = [r for r in rows
                  if r["winner"] in r["raw"]
                  and seg in tags(r["raw"][r["winner"]])]
        entry = {"honmei_races": len(h_rows), "winner_races": len(w_rows)}
        if h_rows:
            entry["honmei_win_diff"] = round(
                sum(r["cand"]["honmei_win"] - r["base"]["honmei_win"]
                    for r in h_rows) / len(h_rows), 4)
        if w_rows:
            entry["winner_logprob_diff"] = round(
                sum(math.log(max(r["cand_winner_prob"], 1e-12))
                    - math.log(max(r["base_winner_prob"], 1e-12))
                    for r in w_rows) / len(w_rows), 4)
            entry["winner_rank_diff"] = round(
                sum((r["cand"]["winner_rank"] or 99)
                    - (r["base"]["winner_rank"] or 99)
                    for r in w_rows) / len(w_rows), 3)
        report[seg] = entry
    return report


def main() -> int:
    feats = pickle.loads((common.SCRATCH / "m2_features.pkl").read_bytes())
    nar_records, jra_records = common.load_records()
    bases, vb_results = common.load_primary_window()
    db = common.corpus()
    segment_of = {r[0]: r[1] for r in db.execute(
        "SELECT race_id, segment FROM races")}
    report = {"stat_features": STAT_FEATURES, "boxes": {}}

    box = "nar"
    seg = SEG_OF_BOX[box]
    bundles = prepare(nar_records, feats, seg)
    pool = [b for b in bundles if b["date"] <= "2026-10-27"]
    gamma_fixed, ll_f, n_f = fit_gamma(pool, "z_fixed", "nar-fixed")
    gamma_decay, ll_d, n_d = fit_gamma(pool, "z_decay", "nar-decay")
    early = [b for b in bundles if b["date"] <= "2026-08-31"]
    gamma_a_fixed, _, _ = fit_gamma(early, "z_fixed", "nar-cons-fixed")
    gamma_a_decay, _, _ = fit_gamma(early, "z_decay", "nar-cons-decay")
    w = {"gamma_fixed": gamma_fixed, "fit_ll_fixed": round(ll_f, 4),
         "gamma_decay": gamma_decay, "fit_ll_decay": round(ll_d, 4),
         "fit_races": n_f}
    late = [b for b in bundles if "2026-09-01" <= b["date"] <= "2026-10-27"]
    for arm, g_c, g_m, zkey in (
            ("fixed", gamma_a_fixed, gamma_fixed, "z_fixed"),
            ("decay", gamma_a_decay, gamma_decay, "z_decay")):
        rows_a = judge_detail(late, g_c, zkey, "regen")
        w[f"consistency_{arm}"] = common.paired_block(to_pairs(rows_a))
        w[f"consistency_{arm}_segments"] = segment_report(rows_a)
    # primary window vs production
    prim_bundles = []
    for rid, pb in bases.items():
        if rid.startswith("jra-"):
            continue
        if segment_of.get(rid) != "nar":
            continue
        res = vb_results.get(rid)
        if res is None or res["winner"] is None:
            continue
        f = feats.get(rid, {})
        raw = {n: f.get(n, {}) for n in pb["p_cal"]}
        z_fixed = common.zscore(raw, STAT_FEATURES)
        z_decay = {}
        for n, zz in z_fixed.items():
            starts = raw[n].get("career_starts") or 0
            d = 1.0 / (1.0 + starts / 4.0)
            z_decay[n] = {k: v * d for k, v in zz.items()}
        prim_bundles.append({
            "race_id": rid, "date": rid[4:14], "p_cal": pb["p_cal"],
            "odds": pb["odds"], "z_fixed": z_fixed, "z_decay": z_decay,
            "raw": raw, "winner": res["winner"], "finish": res["finish"],
            "tri": res["tri"]})
    for arm, g_m, zkey in (("fixed", gamma_fixed, "z_fixed"),
                           ("decay", gamma_decay, "z_decay")):
        rows_p = judge_detail(prim_bundles, g_m, zkey, "production",
                              prod=bases)
        w[f"primary_{arm}"] = common.paired_block(to_pairs(rows_p))
        w[f"primary_{arm}_segments"] = segment_report(rows_p)
        csv_path = common.SCRATCH / f"m2_primary_pairs_nar_{arm}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh)
            wr.writerow(["race_id", "date", "winner", "base_honmei",
                         "cand_honmei", "base_winner_rank",
                         "cand_winner_rank", "base_ll", "cand_ll",
                         "b36_base", "b36_cand", "r24_base", "r24_cand",
                         "tri"])
            for r in rows_p:
                wr.writerow([r["race_id"], r["date"], r["winner"],
                             r["base_honmei"], r["cand_honmei"],
                             r["base"]["winner_rank"],
                             r["cand"]["winner_rank"],
                             round(r["base"]["logloss"], 4),
                             round(r["cand"]["logloss"], 4),
                             int(r["base"]["b36_hit"]),
                             int(r["cand"]["b36_hit"]),
                             int(r["base"]["r24_hit"]),
                             int(r["cand"]["r24_hit"]), r["tri"]])
    report["boxes"]["nar"] = w

    # JRA: coverage evidence only (no pool-era pedigree -> no fit)
    jra_prim = {}
    seg_counts = {}
    for rid, pb in bases.items():
        if not rid.startswith("jra-"):
            continue
        if segment_of.get(rid) not in ("jra_flat",):
            continue
        f = feats.get(rid, {})
        for n, entry in f.items():
            if n not in pb["p_cal"]:
                continue
            b = career_bucket(entry.get("career_starts") or 0)
            c = seg_counts.setdefault(b, {"runners": 0, "with_feature": 0})
            c["runners"] += 1
            if any(entry.get(k) is not None for k in STAT_FEATURES):
                c["with_feature"] += 1
    jra_prim["primary_window_career_segments"] = seg_counts
    report["boxes"]["jra"] = jra_prim
    (common.SCRATCH / "m2_judgement.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
