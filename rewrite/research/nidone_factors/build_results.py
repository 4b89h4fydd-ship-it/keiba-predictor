"""Results universe + per-horse history for the NIDONE-factor corpus.

Merges every in-house result source (verify base, the NAR-rebuild and
JRA-structural record sets, the v10ml dataset) into one results table
keyed by race_id, audits cross-source agreement, then builds:

  results       race_id -> {number: finish}, trifecta payout, source
  history       one row per (natkey, date, track, race_number): the
                horse's own finish/margin in that race, merged from
                card past-run records (pre-race view) and from the
                results universe applied to that race's card runners
                (official outcome).  Conflicts are counted, not hidden.
  race_fields   reconstructed finisher lists per race key from the
                history table (what the opponent graph can see).

Time discipline: history rows are facts about races that have already
been run; feature builders must still filter by date < target date.
"""
from __future__ import annotations

import json
import pickle
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
SCRATCH = PROJECT / "var" / "scratch" / "nidone-factors-20261109"
CORPUS = SCRATCH / "corpus.sqlite3"


def load_pickle(path):
    with open(path, "rb") as fh:
        return pickle.load(fh)


def main() -> int:
    db = sqlite3.connect(CORPUS)
    db.executescript(
        """
        DROP TABLE IF EXISTS results;
        CREATE TABLE results (
          race_id TEXT PRIMARY KEY, finish_json TEXT, tri_payout INTEGER,
          source TEXT);
        DROP TABLE IF EXISTS history;
        CREATE TABLE history (
          natkey TEXT, run_date TEXT, track TEXT, race_number INTEGER,
          finish INTEGER, field_size INTEGER, margin_seconds REAL,
          time_behind REAL, surface TEXT, distance INTEGER,
          from_past_runs INTEGER, from_result INTEGER,
          PRIMARY KEY (natkey, run_date, track, race_number));
        CREATE INDEX idx_hist_key ON history(run_date, track, race_number);
        CREATE INDEX idx_hist_horse ON history(natkey, run_date);
        """
    )
    merged: dict[str, tuple[dict, object, str]] = {}
    agree = Counter()
    disagree = []

    def offer(race_id, finishers, tri, source, priority):
        if not finishers:
            return
        fin = {int(k): int(v) for k, v in finishers.items()
               if v is not None and int(v) > 0}
        if not fin:
            return
        if race_id in merged:
            old_fin, _, old_src, _p = merged[race_id]
            if old_fin == fin:
                agree[source] += 1
            else:
                disagree.append((race_id, old_src, source))
            if priority <= merged[race_id][3]:
                return
        merged[race_id] = (fin, tri, source, priority)

    # priority 3: verify base (officially collated, repaired payouts)
    vb = sqlite3.connect(PROJECT / "var" / "seals" / "verify_base.sqlite3")
    for race_id, finish, payouts in vb.execute(
            "SELECT race_id, finish, payouts_tri FROM results"):
        fin = json.loads(finish) if finish else None
        tri = None
        if payouts:
            pj = json.loads(payouts)
            if pj:
                tri = next(iter(pj.values()))
        offer(race_id, fin, tri, "verify_base", 3)
    vb.close()
    # priority 2: rebuild / structural record sets
    for path, src in (
            (PROJECT / "var/scratch/nar-rebuild-20261109/records.pkl", "nar_rebuild"),
            (PROJECT / "var/scratch/jra-structural-20261109/records_fit.pkl", "jra_struct"),
            (PROJECT / "var/scratch/jra-structural-20261109/records_judge.pkl", "jra_struct")):
        for r in load_pickle(path):
            offer(r["race_id"], r.get("finishers"), r.get("tri_payout"), src, 2)
    # priority 1: v10ml dataset
    for r in load_pickle(PROJECT / "var/scratch/v10ml-20261109/dataset.pkl"):
        offer(r["race_id"], r.get("finishers"), r.get("tri_payout"), "v10ml", 1)

    for race_id, (fin, tri, src, _) in merged.items():
        db.execute("INSERT INTO results VALUES (?,?,?,?)",
                   (race_id, json.dumps(fin), tri, src))
    db.commit()
    print("results races:", len(merged), "cross-source agree:", dict(agree),
          "disagree:", len(disagree), disagree[:5])

    # ---- history from past-run records (dedupe by modal finish) ----
    votes: dict[tuple, Counter] = defaultdict(Counter)
    margins: dict[tuple, list] = defaultdict(list)
    meta: dict[tuple, tuple] = {}
    for nk, rdate, track, rnum, fin, fsize, msec, tbehind, surf, dist in db.execute(
            "SELECT owner_natkey, run_date, track, race_number, finish,"
            " field_size, margin_seconds, time_behind, surface, distance"
            " FROM past_runs WHERE owner_natkey IS NOT NULL"
            " AND run_date IS NOT NULL AND track IS NOT NULL"
            " AND race_number IS NOT NULL AND finish IS NOT NULL"
            " AND finish > 0 AND did_not_run = 0"):
        key = (nk, rdate, track, int(rnum))
        votes[key][int(fin)] += 1
        if msec is not None:
            margins[key].append((msec, tbehind))
        meta[key] = (fsize, surf, dist)
    hist: dict[tuple, dict] = {}
    pr_conflicts = 0
    for key, cnt in votes.items():
        if len(cnt) > 1:
            pr_conflicts += 1
        fin = cnt.most_common(1)[0][0]
        ms = margins.get(key) or []
        msec = sorted(x[0] for x in ms)[len(ms) // 2] if ms else None
        tb = sorted(x[1] for x in ms if x[1] is not None)
        tbv = tb[len(tb) // 2] if tb else None
        fsize, surf, dist = meta[key]
        hist[key] = dict(finish=fin, field_size=fsize, margin=msec,
                         time_behind=tbv, surface=surf, distance=dist,
                         from_pr=1, from_res=0)
    print("history from past_runs:", len(hist), "finish-vote conflicts:", pr_conflicts)

    # ---- merge the results universe applied to card runners ----
    runners: dict[str, list] = defaultdict(list)
    for race_id, number, nk in db.execute(
            "SELECT race_id, number, natkey FROM runners WHERE natkey IS NOT NULL"):
        runners[race_id].append((int(number), nk))
    race_meta = {r[0]: (r[1], r[2], r[3]) for r in db.execute(
        "SELECT race_id, race_date, track, race_number FROM races")}
    res_conflicts = 0
    res_added = 0
    for race_id, finish_json, _, _ in db.execute(
            "SELECT race_id, finish_json, tri_payout, source FROM results"):
        if race_id not in race_meta:
            continue
        rdate, track, rnum = race_meta[race_id]
        fin = {int(k): v for k, v in json.loads(finish_json).items()}
        fsize = max(fin.values()) if fin else None
        for number, nk in runners.get(race_id, []):
            if number not in fin:
                continue
            key = (nk, rdate, track, int(rnum))
            if key in hist:
                if hist[key]["finish"] != fin[number]:
                    res_conflicts += 1
                hist[key]["from_res"] = 1
            else:
                hist[key] = dict(finish=fin[number], field_size=fsize,
                                 margin=None, time_behind=None, surface=None,
                                 distance=None, from_pr=0, from_res=1)
                res_added += 1
    print("history merged:", len(hist), "result-vs-passtrun finish conflicts:",
          res_conflicts, "result-only rows added:", res_added)
    for (nk, rdate, track, rnum), h in hist.items():
        db.execute(
            "INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (nk, rdate, track, rnum, h["finish"], h["field_size"],
             h["margin"], h["time_behind"], h["surface"], h["distance"],
             h["from_pr"], h["from_res"]))
    db.commit()
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
