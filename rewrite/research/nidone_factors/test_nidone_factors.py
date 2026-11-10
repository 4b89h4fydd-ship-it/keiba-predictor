"""Section-8 test suite for the NIDONE-factor research program.

Run: python3 -m pytest rewrite/research/nidone_factors/test_nidone_factors.py
or plain: python3 rewrite/research/nidone_factors/test_nidone_factors.py
Every test prints PASS/FAIL and the runner exits non-zero on failure.
"""
from __future__ import annotations

import json
import math
import pickle
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def t_identity_collisions():
    db = common.corpus()
    dup_runners = db.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM runners"
        " GROUP BY race_id, number HAVING COUNT(*) > 1)").fetchone()[0]
    ped_conflicts = db.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM pedigree"
        " GROUP BY natkey HAVING COUNT(DISTINCT sire) > 1"
        " OR COUNT(DISTINCT dam) > 1)").fetchone()[0]
    check("identity: no duplicate (race, number) runners", dup_runners == 0,
          f"dups={dup_runners}")
    check("identity: natkey has one pedigree parent set", ped_conflicts == 0,
          f"conflicts={ped_conflicts}")


def t_join_correctness():
    db = common.corpus()
    res = {r[0]: {int(k): v for k, v in json.loads(r[1]).items()}
           for r in db.execute("SELECT race_id, finish_json FROM results"
                               " WHERE finish_json IS NOT NULL")}
    race_by_key = {(r[1], r[2], int(r[3])): r[0] for r in db.execute(
        "SELECT race_id, race_date, track, race_number FROM races")}
    number_of = {(r[0], r[2]): int(r[1]) for r in db.execute(
        "SELECT race_id, number, natkey FROM runners")}
    agree = disagree = checked = 0
    for tdate, track, rnum, nk, fin in db.execute(
            "SELECT run_date, track, race_number, owner_natkey, finish"
            " FROM past_runs WHERE race_number IS NOT NULL AND finish > 0"
            " LIMIT 60000"):
        rid = race_by_key.get((tdate, track, rnum))
        if rid is None or rid not in res:
            continue
        num = number_of.get((rid, nk))
        if num is None:
            continue
        rf = res[rid].get(num)
        if rf is None:
            continue
        checked += 1
        if rf == fin:
            agree += 1
        else:
            disagree += 1
    rate = agree / checked if checked else 0
    check("join: past-run finish agrees with result finish >= 99.9%",
          checked > 1000 and rate >= 0.999,
          f"checked={checked} agree={agree} disagree={disagree}")


def t_leakage_boundaries():
    hist = common.History.__new__(common.History)
    from collections import defaultdict
    hist.by_horse = {"h": [("2026-01-01", "X", 1, 3, 10, None),
                           ("2026-01-10", "X", 2, 1, 10, None),
                           ("2026-01-20", "X", 3, 2, 10, None)]}
    hist._dates = {"h": ["2026-01-01", "2026-01-10", "2026-01-20"]}
    hist.by_key = defaultdict(list)
    mid = hist.subsequent("h", "2026-01-01", "2026-01-20")
    check("leakage: subsequent window is (after, before) exclusive",
          [r[0] for r in mid] == ["2026-01-10"], f"got={mid}")
    same_day = hist.subsequent("h", "2026-01-10", "2026-01-10")
    check("leakage: same-day window is empty", same_day == [])
    on_before = hist.subsequent("h", "2026-01-01", "2026-01-10")
    check("leakage: a start ON the cutoff date is excluded",
          on_before == [])


def t_pedigree_missingness():
    feats = pickle.loads((common.SCRATCH / "m2_features.pkl").read_bytes())
    db = common.corpus()
    ped_keys = {r[0] for r in db.execute("SELECT natkey FROM pedigree")}
    runners = {}
    for rid, number, nk in db.execute(
            "SELECT race_id, number, natkey FROM runners"):
        runners[(rid, int(number))] = nk
    from m2_features import FEATURES
    bad = 0
    sampled = 0
    for rid, per in feats.items():
        for number, entry in per.items():
            nk = runners.get((rid, number))
            if nk is None or nk in ped_keys:
                continue
            sampled += 1
            if any(entry.get(k) is not None for k in FEATURES):
                bad += 1
    check("pedigree: no pedigree row -> all features missing (no fill)",
          sampled > 100 and bad == 0, f"sampled={sampled} bad={bad}")


def t_bias_tables():
    blob = pickle.loads((common.SCRATCH / "m3_features.pkl").read_bytes())
    fn = blob["frame_table_n"]
    sn = blob["style_table_n"]
    total_f = sum(fn.values())
    check("bias: frame cell counts are positive and bounded",
          fn and all(v > 0 for v in fn.values())
          and total_f <= blob["residual_rows"],
          f"cells={len(fn)} rows_in_cells={total_f}")
    ter = blob["terciles"]
    check("bias: style terciles ordered per box",
          all(v[0] < v[1] for v in ter.values()), f"{ter}")


def t_probability_and_marks():
    p_cal = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}
    odds = {1: 2.0, 2: 3.0, 3: 5.0, 4: 9.0}
    z = {n: {"f3n": 0.5} for n in p_cal}
    got = common.candidate_probs(p_cal, odds, z, {"f3n": 0.3})
    (win, top3), marks = got
    check("probs: candidate win probabilities sum to 1",
          abs(sum(win.values()) - 1.0) < 1e-6,
          f"sum={sum(win.values())}")
    ranked = sorted(win, key=lambda n: (-win[n], -top3[n], n))
    expect = {n: s for n, s in zip(ranked,
                                   ["◎", "○", "▲", "△", "☆"][:len(ranked)])}
    check("marks: marks are the top-5 by (win, top3) with house symbols",
          marks == expect, f"marks={marks}")


def t_prerace_reproduction():
    """Regenerated base (gamma=0, records) vs the verify base's
    inverted base on the races both cover: the two routes to the
    v9b base must land close (they differ by construction route,
    so this is a loose agreement bound, reported numerically)."""
    nar_records, jra_records = common.load_records()
    bases, _ = common.load_primary_window()
    diffs = []
    for records, seg in ((nar_records, "nar"), (jra_records, "jra_flat")):
        from rewrite.analysis.shadow_v8 import BETAS, WEIGHTS
        for rec in records:
            if rec["segment"] != seg or rec["race_id"] not in bases:
                continue
            status, strengths = common.base_strengths(
                rec, WEIGHTS[seg], BETAS[seg])
            if status != "ok":
                continue
            p_cal = common.pcal_from_strengths(strengths)
            got = common.plain_probs(p_cal, rec.get("win_odds") or {})
            if got is None:
                continue
            (win, _t), _m = got
            stored = bases[rec["race_id"]]["stored_probs"]
            common_nums = [n for n in win if n in stored]
            if len(common_nums) >= 5:
                diffs.append(sum(abs(win[n] - stored[n])
                                 for n in common_nums) / len(common_nums))
    mean_diff = sum(diffs) / len(diffs) if diffs else 9.9
    check("reproduction: regen base vs production form mean |dp| < 0.05",
          len(diffs) >= 100 and mean_diff < 0.05,
          f"races={len(diffs)} mean_abs_diff={mean_diff:.4f}")


def t_segment_exclusions():
    db = common.corpus()
    obihiro = db.execute(
        "SELECT COUNT(*) FROM races WHERE track = '帯広'").fetchone()[0]
    check("segments: Obihiro (obihiro) excluded from the corpus",
          obihiro == 0, f"obihiro_races={obihiro}")
    seg_of = {r[0]: r[1] for r in db.execute(
        "SELECT race_id, segment FROM races")}
    bad = 0
    total = 0
    for name in ("m1_primary_pairs_nar.csv", "m1_primary_pairs_jra.csv",
                 "m2_primary_pairs_nar_fixed.csv",
                 "m2_primary_pairs_nar_decay.csv"):
        import csv as _csv
        with open(common.SCRATCH / name, encoding="utf-8") as fh:
            for row in _csv.DictReader(fh):
                total += 1
                if seg_of.get(row["race_id"]) not in ("nar", "jra_flat"):
                    bad += 1
    check("segments: primary pairs contain only flat races",
          total > 0 and bad == 0, f"pairs={total} bad={bad}")


def t_production_untouched():
    vb = sqlite3.connect(common.VERIFY_BASE)
    ab = vb.execute("SELECT COUNT(*) FROM ability_bases").fetchone()[0]
    ab_ok = vb.execute(
        "SELECT COUNT(*) FROM ability_bases WHERE ok = 1").fetchone()[0]
    res = vb.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    vb.close()
    check("production: verify base contents unchanged (260/240/596)",
          (ab, ab_ok, res) == (260, 240, 596),
          f"ability_bases={ab} ok={ab_ok} results={res}")


def main() -> int:
    t_identity_collisions()
    t_join_correctness()
    t_leakage_boundaries()
    t_pedigree_missingness()
    t_bias_tables()
    t_probability_and_marks()
    t_prerace_reproduction()
    t_segment_exclusions()
    t_production_untouched()
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
