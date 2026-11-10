"""M1 fit + judgement (preregistration sections 2-4, 8).

Arms: A = v9b base, B = A + M1 features, C = Elo-removed base + M1.
Fit: coordinate ascent on final-probability logloss over the pool
window (house rule).  Judgement: primary vs the production final
form on 2026-11-04..08 (verify-base inverted bases), consistency
window A on the pool-late holdout vs the same-material regeneration,
arm C on the regeneration basis.  Day-cluster bootstrap CIs.
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

FEATURE_KEYS = ["f1", "f2", "f3n", "f4n", "f5n", "f6", "f7",
                "f1_1", "f2_1", "f3n_1", "f5n_1"]
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


def prepare(records, feats, segment, weights):
    """Regeneration-basis race bundles for one segment."""
    out = []
    beta = BETAS[segment]
    for rec in records:
        if rec["segment"] != segment:
            continue
        status, strengths = common.base_strengths(rec, weights, beta)
        if status != "ok":
            continue
        p_cal = common.pcal_from_strengths(strengths)
        f = feats.get(rec["race_id"], {})
        z = common.zscore(
            {n: f.get(n, {}) for n in p_cal}, FEATURE_KEYS)
        out.append({
            "race_id": rec["race_id"], "date": rec["date"],
            "p_cal": p_cal, "odds": rec.get("win_odds") or {},
            "z": z, "winner": rec.get("winner"),
            "finish": rec.get("finishers") or {},
            "tri": rec.get("tri_payout"),
        })
    return out


def fit_gamma(bundles, label):
    cache_path = common.SCRATCH / "m1_gamma_cache.json"
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if label in cache:
        print(f"fit[{label}] loaded from cache", flush=True)
        c = cache[label]
        return c["gamma"], c["ll"], c["n"]
    fit = [b for b in bundles if b["winner"] in b["p_cal"]]
    gamma = {k: 0.0 for k in FEATURE_KEYS}

    def objective(g):
        tot = 0.0
        for b in fit:
            probs = final_win_probs(b["p_cal"], b["odds"], b["z"], g)
            if probs is None:
                return math.inf
            tot += -math.log(max(probs.get(b["winner"], 0.0), 1e-12))
        return tot / len(fit)

    cur = objective(gamma)
    for step in (0.4, 0.2, 0.1, 0.05, 0.025, 0.01):
        improved = True
        while improved:
            improved = False
            for k in FEATURE_KEYS:
                for delta in (step, -step):
                    trial = dict(gamma)
                    trial[k] = max(-2.0, min(2.0, trial[k] + delta))
                    if trial[k] == gamma[k]:
                        continue
                    val = objective(trial)
                    if val < cur - 1e-7:
                        gamma, cur = trial, val
                        improved = True
        print(f"fit[{label}] step done ll={cur:.4f} gamma={gamma}", flush=True)
    cache[label] = {"gamma": gamma, "ll": cur, "n": len(fit)}
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    return gamma, cur, len(fit)


def judge(bundles, gamma, base_mode, prod=None):
    """pairs for paired_block.  base_mode: 'regen' (gamma=0 on the
    same bundles) or 'production' (prod = verify-base maps)."""
    pairs = []
    for b in bundles:
        rid = b["race_id"]
        if b["winner"] is None:
            continue
        got = common.candidate_probs(b["p_cal"], b["odds"], b["z"], gamma)
        if got is None:
            continue
        (cwin, ctop3), cmarks = got
        cand_m = common.race_metrics(cwin, cmarks, b["finish"],
                                     b["winner"], b["tri"])
        if base_mode == "production":
            pb = prod[rid]
            base_m = common.race_metrics(
                pb["stored_probs"],
                pb["stored_marks"], b["finish"], b["winner"], b["tri"])
            odds = pb["odds"]
        else:
            got0 = common.plain_probs(b["p_cal"], b["odds"])
            if got0 is None:
                continue
            (bwin, btop3), bmarks = got0
            base_m = common.race_metrics(bwin, bmarks, b["finish"],
                                         b["winner"], b["tri"])
            odds = b["odds"]
        fav = min(odds, key=lambda n: (odds[n], n)) if odds else None
        pairs.append({"date": b["date"], "base": base_m, "cand": cand_m,
                      "favourite_win": 1.0 if fav == b["winner"] else 0.0,
                      "race_id": rid})
    return pairs


def main() -> int:
    feats = pickle.loads((common.SCRATCH / "m1_features.pkl").read_bytes())
    nar_records, jra_records = common.load_records()
    bases, vb_results = common.load_primary_window()
    db = common.corpus()
    segment_of = {r[0]: r[1] for r in db.execute(
        "SELECT race_id, segment FROM races")}
    report = {"features": FEATURE_KEYS, "windows": {}}

    all_records = {"nar": nar_records, "jra": jra_records}
    for box in ("nar", "jra"):
        seg = SEG_OF_BOX[box]
        records = all_records[box]
        bundles = prepare(records, feats, seg, WEIGHTS[seg])
        bundles_c = prepare(records, feats, seg,
                            common.weights_without_elo(seg))
        pool = [b for b in bundles if b["date"] <= "2026-10-27"]
        pool_c = [b for b in bundles_c if b["date"] <= "2026-10-27"]
        gamma_main, ll_main, n_main = fit_gamma(pool, f"{box}-main")
        gamma_c, ll_c, n_c = fit_gamma(pool_c, f"{box}-elo-removed")
        early = [b for b in bundles if b["date"] <= "2026-08-31"]
        gamma_a, ll_a, n_a = fit_gamma(early, f"{box}-consistency")
        report["windows"][box] = {
            "gamma_main": gamma_main, "fit_ll_main": round(ll_main, 4),
            "fit_races_main": n_main,
            "gamma_consistency": gamma_a, "fit_ll_consistency": round(ll_a, 4),
            "fit_races_consistency": n_a,
            "gamma_elo_removed": gamma_c, "fit_ll_elo_removed": round(ll_c, 4),
        }
        # consistency window A: 2026-09-01..10-27 vs regen base
        late = [b for b in bundles
                if "2026-09-01" <= b["date"] <= "2026-10-27"]
        pairs_a = judge(late, gamma_a, "regen")
        report["windows"][box]["consistency_window"] = common.paired_block(pairs_a)
        # arm C on the primary-window dates (regen basis, both boxes'
        # records cover them), base = elo-removed regen
        prim_dates = {b["race_id"] for b in bundles
                      if b["date"] >= "2026-11-04"}
        late_c = [b for b in bundles_c if b["race_id"] in prim_dates]
        by_id = {b["race_id"]: b for b in bundles}
        pairs_c = []
        for bc in late_c:
            b0 = by_id.get(bc["race_id"])
            if b0 is None or bc["winner"] is None:
                continue
            got_c = common.candidate_probs(bc["p_cal"], bc["odds"],
                                           bc["z"], gamma_c)
            got_0 = common.plain_probs(bc["p_cal"], bc["odds"])
            if got_c is None or got_0 is None:
                continue
            (cw, ct), cm = got_c
            (bw, bt), bm = got_0
            pairs_c.append({
                "date": bc["date"],
                "base": common.race_metrics(bw, bm, bc["finish"],
                                            bc["winner"], bc["tri"]),
                "cand": common.race_metrics(cw, cm, bc["finish"],
                                            bc["winner"], bc["tri"]),
                "favourite_win": 0.0, "race_id": bc["race_id"]})
            # favourite from record odds for arm C block context
            odds = bc["odds"]
            if odds:
                fav = min(odds, key=lambda n: (odds[n], n))
                pairs_c[-1]["favourite_win"] = 1.0 if fav == bc["winner"] else 0.0
        report["windows"][box]["armC_vs_elo_removed_base"] = \
            common.paired_block(pairs_c)
        # primary window vs production final form
        prim_bundles = []
        for rid, pb in bases.items():
            if (rid.startswith("jra-")) != (box == "jra"):
                continue
            if segment_of.get(rid) not in ("nar", "jra_flat"):
                continue  # newcomers / jumps stay out of flat judging
            res = vb_results.get(rid)
            if res is None or res["winner"] is None:
                continue
            f = feats.get(rid, {})
            z = common.zscore({n: f.get(n, {}) for n in pb["p_cal"]},
                              FEATURE_KEYS)
            prim_bundles.append({
                "race_id": rid, "date": rid[4:14], "p_cal": pb["p_cal"],
                "odds": pb["odds"], "z": z, "winner": res["winner"],
                "finish": res["finish"], "tri": res["tri"]})
        pairs_p = judge(prim_bundles, gamma_main, "production", prod=bases)
        report["windows"][box]["primary_vs_production"] = \
            common.paired_block(pairs_p)
        # per-race CSV for the primary window
        csv_path = common.SCRATCH / f"m1_primary_pairs_{box}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["race_id", "date", "winner", "base_honmei",
                        "cand_honmei", "base_winner_rank",
                        "cand_winner_rank", "base_ll", "cand_ll",
                        "b36_base", "b36_cand", "r24_base", "r24_cand", "tri"])
            by_rid = {b["race_id"]: b for b in prim_bundles}
            for p in pairs_p:
                b = by_rid[p["race_id"]]
                pb = bases[p["race_id"]]
                bh = next((n for n, m in pb["stored_marks"].items()
                           if m == "◎"), None)
                got = common.candidate_probs(b["p_cal"], b["odds"],
                                             b["z"], gamma_main)
                (cw, _ct), cmarks = got
                ch = next((n for n, m in cmarks.items() if m == "◎"), None)
                w.writerow([p["race_id"], p["date"], b["winner"], bh, ch,
                            p["base"]["winner_rank"], p["cand"]["winner_rank"],
                            round(p["base"]["logloss"], 4),
                            round(p["cand"]["logloss"], 4),
                            int(p["base"]["b36_hit"]), int(p["cand"]["b36_hit"]),
                            int(p["base"]["r24_hit"]), int(p["cand"]["r24_hit"]),
                            b["tri"]])
        print(box, "primary pairs:", len(pairs_p),
              "consistency pairs:", len(pairs_a), flush=True)
    (common.SCRATCH / "m1_judgement.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
