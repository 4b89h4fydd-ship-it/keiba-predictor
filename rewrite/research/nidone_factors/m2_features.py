"""M2 feature builder: pedigree produce/sibling aggregates derived
from our own stored results (preregistration section 5).

Groups (keyed by the already-collected parent NAMES): sire (all /
turf / dirt), damsire (all), dam (all = maternal siblings).  For each
group, over starts STRICTLY BEFORE the target race date, excluding
the runner itself: win rate, top-3 rate, finish percentile
(sign-flipped) and the start count.  Groups with < 10 starts stay
missing.  Parent names are never guessed; a missing pedigree row
means all features missing.
"""
from __future__ import annotations

import json
import pickle
import sys
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

MIN_STARTS = 10
GROUPS = ("sire", "sire_turf", "sire_dirt", "damsire", "dam")
FEATURES = ([f"{g}_{s}" for g in GROUPS for s in ("win", "top3", "pctn")]
            + ["sire_n", "damsire_n", "dam_n"])
JRA_TRACKS = {"札幌", "函館", "福島", "新潟", "東京", "中山",
              "中京", "京都", "阪神", "小倉"}


def build_parent_index(db):
    ped = {}
    for nk, sire, dam, damsire in db.execute(
            "SELECT natkey, sire, dam, damsire FROM pedigree"):
        ped[nk] = (sire, dam, damsire)
    def norm_surf(s):
        return "ダート" if s == "ダ" else s

    surf_by_key = {(d, t, int(n)): norm_surf(s) for d, t, n, s in db.execute(
        "SELECT race_date, track, race_number, surface FROM races")}
    surf_by_run = {}
    for nk, rdate, track, rnum, surf in db.execute(
            "SELECT owner_natkey, run_date, track, race_number, surface"
            " FROM past_runs WHERE race_number IS NOT NULL"):
        surf_by_run[(nk, rdate, track, int(rnum))] = norm_surf(surf)
    starts = defaultdict(list)
    for nk, rdate, track, rnum, fin, fsize in db.execute(
            "SELECT natkey, run_date, track, race_number, finish,"
            " field_size FROM history WHERE finish > 0"):
        if nk not in ped:
            continue
        surface = surf_by_key.get((rdate, track, int(rnum))) or \
            surf_by_run.get((nk, rdate, track, int(rnum)))
        sire, dam, damsire = ped[nk]
        pct = (fin / fsize) if fsize else None
        item = (rdate, 1.0 if fin == 1 else 0.0,
                1.0 if fin <= 3 else 0.0, pct, nk)
        if sire:
            starts[("sire", sire)].append(item)
            if surface == "芝":
                starts[("sire_turf", sire)].append(item)
            elif surface == "ダート":
                starts[("sire_dirt", sire)].append(item)
        if damsire:
            starts[("damsire", damsire)].append(item)
        if dam:
            starts[("dam", dam)].append(item)
    index = {}
    for key, items in starts.items():
        items.sort(key=lambda x: x[0])
        index[key] = ([x[0] for x in items], items)
    return ped, index


def group_stats(index, group, parent, before_date, self_nk):
    found = index.get((group, parent))
    if not found:
        return None, 0
    dates, items = found
    hi = bisect_left(dates, before_date)
    sel = [x for x in items[:hi] if x[4] != self_nk]
    n = len(sel)
    if n == 0:
        return None, 0
    win = sum(x[1] for x in sel) / n
    top3 = sum(x[2] for x in sel) / n
    pcts = [x[3] for x in sel if x[3] is not None]
    pctn = -sum(pcts) / len(pcts) if pcts else None
    return (win, top3, pctn), n


def main() -> int:
    db = common.corpus()
    ped, index = build_parent_index(db)
    nar_records, jra_records = common.load_records()
    bases, _ = common.load_primary_window()
    race_ids = {r["race_id"] for r in nar_records}
    race_ids |= {r["race_id"] for r in jra_records}
    race_ids |= set(bases)
    race_info = {r[0]: (r[1], r[2], r[3]) for r in db.execute(
        "SELECT race_id, race_date, surface, distance FROM races")}
    runners = defaultdict(dict)
    for race_id, number, nk in db.execute(
            "SELECT race_id, number, natkey FROM runners"
            " WHERE natkey IS NOT NULL"):
        runners[race_id][int(number)] = nk
    card_runs = defaultdict(list)
    for rid, nk, rdate, surf, dist, track in db.execute(
            "SELECT card_race_id, owner_natkey, run_date, surface,"
            " distance, track FROM past_runs WHERE finish > 0"
            " ORDER BY run_date DESC"):
        card_runs[(rid, nk)].append((rdate, surf, dist, track))
    features = {}
    stats = defaultdict(lambda: {"runners": 0, "with_ped": 0,
                                 "with_any_feature": 0})
    for race_id in sorted(race_ids):
        info = race_info.get(race_id)
        if info is None:
            continue
        tdate, tsurface, tdist = info
        box = "jra" if race_id.startswith("jra-") else "nar"
        per = {}
        for number, nk in runners.get(race_id, {}).items():
            runs = card_runs.get((race_id, nk), [])
            known_surfs = [("ダート" if r[1] == "ダ" else r[1])
                           for r in runs if r[1]]
            entry = {"career_starts": len(runs),
                     "first_surface": bool(known_surfs)
                     and tsurface is not None
                     and all(s != tsurface for s in known_surfs),
                     "distance_change": bool(
                         runs and runs[0][2] and tdist
                         and abs(tdist - runs[0][2]) >= 400),
                     "transfer": bool(runs) and (
                         (runs[0][3] in JRA_TRACKS) != (box == "jra"))}
            p = ped.get(nk)
            if p is None:
                for k in FEATURES:
                    entry[k] = None
            else:
                stats[box]["with_ped"] += 1
                sire, dam, damsire = p
                any_feat = False
                for group, parent in (("sire", sire), ("sire_turf", sire),
                                      ("sire_dirt", sire),
                                      ("damsire", damsire), ("dam", dam)):
                    st, n = group_stats(index, group, parent, tdate, nk)
                    if group in ("sire", "damsire", "dam"):
                        entry[f"{group}_n"] = n
                    if st is None or n < MIN_STARTS:
                        entry[f"{group}_win"] = None
                        entry[f"{group}_top3"] = None
                        entry[f"{group}_pctn"] = None
                    else:
                        entry[f"{group}_win"] = st[0]
                        entry[f"{group}_top3"] = st[1]
                        entry[f"{group}_pctn"] = st[2]
                        any_feat = True
                if any_feat:
                    stats[box]["with_any_feature"] += 1
            stats[box]["runners"] += 1
            per[number] = entry
        features[race_id] = per
    out_path = common.SCRATCH / "m2_features.pkl"
    out_path.write_bytes(pickle.dumps(features))
    summary = {"races": len(features), "features": FEATURES,
               "by_box": {b: dict(s) for b, s in stats.items()}}
    (common.SCRATCH / "m2_feature_stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
