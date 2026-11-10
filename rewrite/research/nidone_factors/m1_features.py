"""M1 feature builder: opponents' subsequent results.

For every runner of every target race, summarises what the opponents
from its recent past races did AFTER those races but strictly BEFORE
the target race's date (the registered same-day boundary).  Features
and aggregation are frozen in preregistration-20261109.md section 4.

Output: var/scratch/nidone-factors-20261109/m1_features.pkl
  {race_id: {number: {feature: value|None, evidence: 0/1}}}
plus m1_feature_stats.json (effective coverage on the used windows).
"""
from __future__ import annotations

import json
import pickle
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

FEATURES = ["f1", "f2", "f3n", "f4n", "f5n", "f6", "f7",
            "f1_1", "f2_1", "f3n_1", "f5n_1"]
RUN_WEIGHTS = (0.5, 0.3, 0.2)


def opponent_block(hist: common.History, owner: str, run, target_date: str):
    """Aggregates over one past run's opponents; None when unusable."""
    rdate, _track, _rnum, own_finish = run[0], run[1], run[2], run[3]
    field_size = run[4]
    field = hist.by_key.get((rdate, run[1], run[2]), [])
    opponents = [x for x in field if x[0] != owner]
    if not opponents:
        return None
    wins, top3s, pcts, tbs = [], [], [], []
    ahead_pcts = []
    winner_top3 = None
    n_with_sub = 0
    for onk, ofin, _ofsize, _otb in opponents:
        subs = hist.subsequent(onk, rdate, target_date)
        if not subs:
            continue
        n_with_sub += 1
        wins.append(sum(1 for s in subs if s[3] == 1) / len(subs))
        top3s.append(sum(1 for s in subs if s[3] <= 3) / len(subs))
        ps = [s[3] / s[4] for s in subs if s[4]]
        if ps:
            pcts.append(sum(ps) / len(ps))
            if ofin < own_finish:
                ahead_pcts.append(sum(ps) / len(ps))
        tv = [s[5] for s in subs if s[5] is not None]
        if tv:
            tbs.append(sum(tv) / len(tv))
        if ofin == 1:
            winner_top3 = sum(1 for s in subs if s[3] <= 3) / len(subs)
    if n_with_sub == 0:
        return None
    denom = (field_size - 1) if field_size else len(opponents)
    return {
        "f1": sum(wins) / len(wins) if wins else None,
        "f2": sum(top3s) / len(top3s) if top3s else None,
        "f3n": -sum(pcts) / len(pcts) if pcts else None,
        "f4n": -sum(tbs) / len(tbs) if tbs else None,
        "f5n": -sum(ahead_pcts) / len(ahead_pcts) if ahead_pcts else None,
        "f6": winner_top3,
        "f7": min(1.0, n_with_sub / denom) if denom else None,
    }


def runner_features(hist, db, race_id, natkey, target_date):
    runs = db.execute(
        "SELECT run_date, track, race_number, finish, field_size"
        " FROM past_runs WHERE card_race_id = ? AND owner_natkey = ?"
        " AND finish IS NOT NULL AND finish > 0 AND did_not_run = 0"
        " AND race_number IS NOT NULL ORDER BY run_date DESC, rowid DESC"
        " LIMIT 3", (race_id, natkey)).fetchall()
    blocks = []
    for run in runs:
        blk = opponent_block(hist, natkey, run, target_date)
        if blk is not None:
            blocks.append(blk)
    if not blocks:
        return {k: None for k in FEATURES} | {"evidence": 0}
    out = {}
    for k in ("f1", "f2", "f3n", "f4n", "f5n", "f6", "f7"):
        num = den = 0.0
        for i, blk in enumerate(blocks):
            if blk.get(k) is not None:
                num += RUN_WEIGHTS[i] * blk[k]
                den += RUN_WEIGHTS[i]
        out[k] = (num / den) if den else None
    first = blocks[0]
    out["f1_1"] = first.get("f1")
    out["f2_1"] = first.get("f2")
    out["f3n_1"] = first.get("f3n")
    out["f5n_1"] = first.get("f5n")
    out["evidence"] = 1
    return out


def main() -> int:
    db = common.corpus()
    hist = common.History(db)
    nar_records, jra_records = common.load_records()
    bases, _ = common.load_primary_window()
    race_ids = {r["race_id"] for r in nar_records}
    race_ids |= {r["race_id"] for r in jra_records}
    race_ids |= set(bases)
    race_date = {r[0]: r[1] for r in db.execute(
        "SELECT race_id, race_date FROM races")}
    runners = defaultdict(dict)
    for race_id, number, nk in db.execute(
            "SELECT race_id, number, natkey FROM runners"
            " WHERE natkey IS NOT NULL"):
        runners[race_id][int(number)] = nk
    features = {}
    stats = defaultdict(lambda: {"races": 0, "runners": 0, "evidence": 0})
    missing_races = 0
    for race_id in sorted(race_ids):
        tdate = race_date.get(race_id)
        if tdate is None:
            missing_races += 1
            continue
        box = "jra" if race_id.startswith("jra-") else "nar"
        per = {}
        for number, nk in runners.get(race_id, {}).items():
            per[number] = runner_features(hist, db, race_id, nk, tdate)
            stats[box]["runners"] += 1
            stats[box]["evidence"] += per[number]["evidence"]
        stats[box]["races"] += 1
        features[race_id] = per
    out_path = common.SCRATCH / "m1_features.pkl"
    out_path.write_bytes(pickle.dumps(features))
    summary = {
        "races": len(features), "missing_race_cards": missing_races,
        "by_box": {b: {"races": s["races"], "runners": s["runners"],
                       "evidence_rate": round(s["evidence"] / s["runners"], 4)
                       if s["runners"] else None}
                   for b, s in stats.items()},
        "features": FEATURES,
    }
    (common.SCRATCH / "m1_feature_stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
