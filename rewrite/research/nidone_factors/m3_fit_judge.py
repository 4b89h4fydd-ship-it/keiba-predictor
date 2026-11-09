"""M3 fit + judgement (preregistration sections 2, 6, 8).

Arms: +frame, +style, +frame x style.  The per-runner inputs are
the measured bias values (static table + trailing-28d weekly part),
standardized within the race like the other candidates.  Also
reports the overlap with the existing pace layer (correlation of
the combined bias input with log pace_factor) and the registered
emphasis slices (JRA turf, 17+ fields, <=1400m) as reporting only.
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

SEG_OF_BOX = {"nar": "nar", "jra": "jra_flat"}
ARM_KEYS = {"frame": ["zf"], "style": ["zs"], "both": ["zf", "zs"]}


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


def make_z(feat_entries, numbers):
    raw = {}
    for n in numbers:
        e = feat_entries.get(n, {})
        raw[n] = {"zf": (e.get("frame_static", 0.0)
                         + e.get("frame_weekly", 0.0)),
                  "zs": (e.get("style_static", 0.0)
                         + e.get("style_weekly", 0.0))}
    return common.zscore(raw, ["zf", "zs"])


def prepare(records, feats, segment):
    out = []
    for rec in records:
        if rec["segment"] != segment:
            continue
        status, strengths = common.base_strengths(
            rec, WEIGHTS[segment], BETAS[segment])
        if status != "ok":
            continue
        p_cal = common.pcal_from_strengths(strengths)
        fe = feats.get(rec["race_id"], {})
        entry0 = next(iter(fe.values()), {}) if fe else {}
        out.append({
            "race_id": rec["race_id"], "date": rec["date"],
            "p_cal": p_cal, "odds": rec.get("win_odds") or {},
            "z": make_z(fe, p_cal.keys()),
            "winner": rec.get("winner"),
            "finish": rec.get("finishers") or {},
            "tri": rec.get("tri_payout"),
            "pace": rec.get("pace_factor") or {},
            "surface": entry0.get("surface"),
            "distance": entry0.get("distance"),
            "field": len(p_cal),
        })
    return out


def fit_gamma(bundles, keys, label):
    cache_path = common.SCRATCH / "m3_gamma_cache.json"
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if label in cache:
        print(f"fit[{label}] loaded from cache", flush=True)
        c = cache[label]
        return c["gamma"], c["ll"], c["n"]
    fit = [b for b in bundles if b["winner"] in b["p_cal"]]
    gamma = {k: 0.0 for k in keys}

    def objective(g):
        tot = 0.0
        for b in fit:
            probs = final_win_probs(b["p_cal"], b["odds"], b["z"], g)
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
            for k in keys:
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


def judge(bundles, gamma, base_mode, prod=None):
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
                pb["stored_probs"], pb["stored_marks"], b["finish"],
                b["winner"], b["tri"])
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
                      "race_id": rid, "surface": b.get("surface"),
                      "distance": b.get("distance"),
                      "field": b.get("field")})
    return pairs


def slice_block(pairs, pred):
    sub = [p for p in pairs if pred(p)]
    return common.paired_block(sub)


def main() -> int:
    blob = pickle.loads((common.SCRATCH / "m3_features.pkl").read_bytes())
    feats = blob["features"]
    nar_records, jra_records = common.load_records()
    bases, vb_results = common.load_primary_window()
    db = common.corpus()
    segment_of = {r[0]: r[1] for r in db.execute(
        "SELECT race_id, segment FROM races")}
    meta = {r[0]: (r[1], r[2]) for r in db.execute(
        "SELECT race_id, surface, distance FROM races")}
    report = {"boxes": {}}
    all_records = {"nar": nar_records, "jra": jra_records}
    for box in ("nar", "jra"):
        seg = SEG_OF_BOX[box]
        bundles = prepare(all_records[box], feats, seg)
        pool = [b for b in bundles if b["date"] <= "2026-10-27"]
        early = [b for b in bundles if b["date"] <= "2026-08-31"]
        late = [b for b in bundles
                if "2026-09-01" <= b["date"] <= "2026-10-27"]
        prim_bundles = []
        for rid, pb in bases.items():
            if (rid.startswith("jra-")) != (box == "jra"):
                continue
            want = "jra_flat" if box == "jra" else "nar"
            if segment_of.get(rid) != want:
                continue
            res = vb_results.get(rid)
            if res is None or res["winner"] is None:
                continue
            fe = feats.get(rid, {})
            surf, dist = meta.get(rid, (None, None))
            prim_bundles.append({
                "race_id": rid, "date": rid[4:14], "p_cal": pb["p_cal"],
                "odds": pb["odds"], "z": make_z(fe, pb["p_cal"].keys()),
                "winner": res["winner"], "finish": res["finish"],
                "tri": res["tri"], "pace": {},
                "surface": surf, "distance": dist,
                "field": len(pb["p_cal"])})
        w = {}
        # pace overlap on the pooled judge material (both arm inputs)
        xs, ys = [], []
        for b in late + prim_bundles:
            for n, pf in (b.get("pace") or {}).items():
                if n in b["z"] and pf and pf > 0:
                    xs.append(b["z"][n]["zf"] + b["z"][n]["zs"])
                    ys.append(math.log(pf))
        if len(xs) > 30:
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            vx = sum((x - mx) ** 2 for x in xs)
            vy = sum((y - my) ** 2 for y in ys)
            w["pace_overlap_corr"] = round(
                cov / math.sqrt(vx * vy), 4) if vx > 0 and vy > 0 else None
            w["pace_overlap_n"] = len(xs)
        for arm, keys in ARM_KEYS.items():
            g_main, ll_main, n_main = fit_gamma(pool, keys, f"{box}-{arm}")
            g_a, _, _ = fit_gamma(early, keys, f"{box}-{arm}-cons")
            w[f"gamma_{arm}"] = g_main
            w[f"fit_ll_{arm}"] = round(ll_main, 4)
            w[f"consistency_{arm}"] = common.paired_block(
                judge(late, g_a, "regen"))
            pairs_p = judge(prim_bundles, g_main, "production", prod=bases)
            w[f"primary_{arm}"] = common.paired_block(pairs_p)
            if arm == "both":
                w["primary_both_slices"] = {
                    "jra_turf": slice_block(
                        pairs_p, lambda p: p["surface"] == "芝"),
                    "field17": slice_block(
                        pairs_p, lambda p: (p["field"] or 0) >= 17),
                    "short1400": slice_block(
                        pairs_p, lambda p: (p["distance"] or 99999) <= 1400),
                }
                csv_path = common.SCRATCH / f"m3_primary_pairs_{box}.csv"
                with open(csv_path, "w", newline="",
                          encoding="utf-8") as fh:
                    wr = csv.writer(fh)
                    wr.writerow(["race_id", "date", "winner",
                                 "base_winner_rank", "cand_winner_rank",
                                 "base_ll", "cand_ll", "b36_base",
                                 "b36_cand", "r24_base", "r24_cand", "tri"])
                    for p in pairs_p:
                        wr.writerow([p["race_id"], p["date"], "",
                                     p["base"]["winner_rank"],
                                     p["cand"]["winner_rank"],
                                     round(p["base"]["logloss"], 4),
                                     round(p["cand"]["logloss"], 4),
                                     int(p["base"]["b36_hit"]),
                                     int(p["cand"]["b36_hit"]),
                                     int(p["base"]["r24_hit"]),
                                     int(p["cand"]["r24_hit"]), ""])
        report["boxes"][box] = w
        print(box, "done", flush=True)
    (common.SCRATCH / "m3_judgement.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("written m3_judgement.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
