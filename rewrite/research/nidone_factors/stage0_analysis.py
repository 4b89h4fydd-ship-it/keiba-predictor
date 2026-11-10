"""Stage 0 audit computations for the NIDONE-factor program.

Reads corpus.sqlite3 (races/runners/past_runs/pedigree/results/history)
and emits stage0_stats.json with every number quoted in the Stage 0
report.  No modelling here.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
SCRATCH = PROJECT / "var" / "scratch" / "nidone-factors-20261109"
DB = SCRATCH / "corpus.sqlite3"


def main() -> int:
    db = sqlite3.connect(DB)
    out: dict = {}

    # ---- population by year x box ----
    pop = {}
    for year, box, n_races, n_runners in db.execute(
            "SELECT substr(race_date,1,4), box, count(*), sum(n_runners)"
            " FROM races GROUP BY 1,2"):
        pop[f"{year}-{box}"] = {"races": n_races, "runners": n_runners}
    out["population"] = pop
    out["segments"] = {r[0]: r[1] for r in db.execute(
        "SELECT segment, count(*) FROM races GROUP BY segment")}
    out["tracks"] = {f"{r[0]}-{r[1]}": r[2] for r in db.execute(
        "SELECT box, track, count(*) FROM races GROUP BY box, track")}

    # ---- result collation ----
    coll = {}
    for box, tot, with_res in db.execute(
            "SELECT r.box, count(*), sum(CASE WHEN res.race_id IS NOT NULL"
            " THEN 1 ELSE 0 END) FROM races r LEFT JOIN results res"
            " ON res.race_id = r.race_id GROUP BY r.box"):
        coll[box] = {"races": tot, "with_result": with_res,
                     "rate": round(with_res / tot, 4)}
    out["result_collation"] = coll

    # ---- pre-race coverage on cards ----
    cov = {}
    for box, n, with_pr, with_odds, with_frame in db.execute(
            "SELECT ra.box, count(*),"
            " sum(CASE WHEN EXISTS (SELECT 1 FROM past_runs p"
            "   WHERE p.card_race_id = ru.race_id AND p.owner_natkey = ru.natkey)"
            "  THEN 1 ELSE 0 END),"
            " sum(CASE WHEN ru.win_odds IS NOT NULL THEN 1 ELSE 0 END),"
            " sum(CASE WHEN ru.frame IS NOT NULL THEN 1 ELSE 0 END)"
            " FROM runners ru JOIN races ra ON ra.race_id = ru.race_id"
            " GROUP BY ra.box"):
        cov[box] = {"runners": n, "with_past_runs": with_pr,
                    "past_run_rate": round(with_pr / n, 4),
                    "odds_rate": round(with_odds / n, 4),
                    "frame_rate": round(with_frame / n, 4)}
    out["card_coverage"] = cov

    # corner positions on past runs (style data)
    style = {}
    for box, n, with_corner in db.execute(
            "SELECT ra.box, count(*), sum(CASE WHEN p.corner_first IS NOT NULL"
            " THEN 1 ELSE 0 END) FROM past_runs p"
            " JOIN races ra ON ra.race_id = p.card_race_id GROUP BY ra.box"):
        style[box] = {"past_runs": n, "corner_rate": round(with_corner / n, 4)}
    out["past_run_corner_coverage"] = style

    # ---- opponent join: reconstruct fields from history ----
    fields: dict[tuple, list] = defaultdict(list)
    for nk, rdate, track, rnum, fin, fsize in db.execute(
            "SELECT natkey, run_date, track, race_number, finish, field_size"
            " FROM history"):
        fields[(rdate, track, rnum)].append((nk, fin, fsize))
    out["history_rows"] = db.execute("SELECT count(*) FROM history").fetchone()[0]
    out["distinct_horses_history"] = db.execute(
        "SELECT count(DISTINCT natkey) FROM history").fetchone()[0]
    out["distinct_race_keys_history"] = len(fields)

    # for every past-run record: how many opponents does the graph see?
    import statistics
    n_rec = n_with_opp = 0
    opp_counts = []
    full_field = 0
    checked = 0
    for nk, rdate, track, rnum in db.execute(
            "SELECT owner_natkey, run_date, track, race_number FROM past_runs"
            " WHERE owner_natkey IS NOT NULL AND finish IS NOT NULL AND finish > 0"):
        n_rec += 1
        fld = fields.get((rdate, track, int(rnum)) if rnum is not None else None)
        if not fld:
            continue
        opps = [x for x in fld if x[0] != nk]
        if opps:
            n_with_opp += 1
            opp_counts.append(len(opps))
            fsize = next((x[2] for x in fld if x[2]), None)
            if fsize and len(fld) >= fsize:
                full_field += 1
            checked += 1
    out["opponent_join"] = {
        "past_run_records": n_rec,
        "with_any_opponent": n_with_opp,
        "rate": round(n_with_opp / n_rec, 4) if n_rec else None,
        "median_opponents": statistics.median(opp_counts) if opp_counts else None,
        "mean_opponents": round(sum(opp_counts) / len(opp_counts), 2) if opp_counts else None,
        "full_field_recovered_share_of_checked": round(full_field / checked, 4) if checked else None,
    }

    # ---- join correctness: past-run finish vs results-universe finish ----
    res = {r[0]: {int(k): v for k, v in json.loads(r[1]).items()} for r in db.execute(
        "SELECT race_id, finish_json FROM results")}
    runner_nat = {}
    for race_id, number, nk in db.execute(
            "SELECT race_id, number, natkey FROM runners"):
        runner_nat[(race_id, int(number))] = nk
    race_key = {r[0]: (r[1], r[2], r[3]) for r in db.execute(
        "SELECT race_id, race_date, track, race_number FROM races")}
    key2race = {v: k for k, v in race_key.items()}
    agree = disagree = checked2 = 0
    examples = []
    for nk, rdate, track, rnum, fin in db.execute(
            "SELECT owner_natkey, run_date, track, race_number, finish"
            " FROM past_runs WHERE finish IS NOT NULL AND finish > 0"
            " AND owner_natkey IS NOT NULL"):
        rid = key2race.get((rdate, track, int(rnum)) if rnum is not None else None)
        if rid is None or rid not in res:
            continue
        # find the owner's number in that race
        num = next((n for (rr, n), k in runner_nat.items()
                    if rr == rid and k == nk), None)
        if num is None or num not in res[rid]:
            continue
        checked2 += 1
        if res[rid][num] == fin:
            agree += 1
        else:
            disagree += 1
            if len(examples) < 5:
                examples.append((rid, num, fin, res[rid][num]))
    out["join_correctness"] = {"checked": checked2, "agree": agree,
                               "disagree": disagree,
                               "rate": round(agree / checked2, 6) if checked2 else None,
                               "examples": examples}

    # ---- natkey collisions (pedigree: same natkey, different parents) ----
    coll_rows = db.execute(
        "SELECT natkey, count(DISTINCT sire || '|' || dam) FROM pedigree"
        " WHERE natkey IS NOT NULL AND sire IS NOT NULL AND dam IS NOT NULL"
        " GROUP BY natkey HAVING count(DISTINCT sire || '|' || dam) > 1"
    ).fetchall()
    out["natkey_collisions"] = {"count": len(coll_rows),
                                "examples": coll_rows[:5]}
    out["distinct_natkeys_runners"] = db.execute(
        "SELECT count(DISTINCT natkey) FROM runners").fetchone()[0]

    # ---- pedigree coverage ----
    ped = {}
    for box, n, with_row, with_sire, with_dam, with_damsire in db.execute(
            "SELECT ra.box, count(*),"
            " sum(CASE WHEN pg.race_id IS NOT NULL THEN 1 ELSE 0 END),"
            " sum(CASE WHEN pg.sire IS NOT NULL AND pg.sire != '' THEN 1 ELSE 0 END),"
            " sum(CASE WHEN pg.dam IS NOT NULL AND pg.dam != '' THEN 1 ELSE 0 END),"
            " sum(CASE WHEN pg.damsire IS NOT NULL AND pg.damsire != '' THEN 1 ELSE 0 END)"
            " FROM runners ru JOIN races ra ON ra.race_id = ru.race_id"
            " LEFT JOIN pedigree pg ON pg.race_id = ru.race_id"
            "   AND pg.horse_number = ru.number GROUP BY ra.box"):
        ped[box] = {"runners": n, "row_rate": round(with_row / n, 4),
                    "sire_rate": round((with_sire or 0) / n, 4),
                    "dam_rate": round((with_dam or 0) / n, 4),
                    "damsire_rate": round((with_damsire or 0) / n, 4)}
    out["pedigree_coverage"] = ped
    # pedigree by era for NAR (backfill claim) and JRA
    ped_era = {}
    for box, era, n, with_row in db.execute(
            "SELECT ra.box, CASE WHEN ra.race_date < '2026-10-28' THEN 'pool'"
            " ELSE 'live' END, count(*),"
            " sum(CASE WHEN pg.race_id IS NOT NULL THEN 1 ELSE 0 END)"
            " FROM runners ru JOIN races ra ON ra.race_id = ru.race_id"
            " LEFT JOIN pedigree pg ON pg.race_id = ru.race_id"
            "   AND pg.horse_number = ru.number GROUP BY ra.box, 2"):
        ped_era[f"{box}-{era}"] = {"runners": n,
                                   "row_rate": round(with_row / n, 4)}
    out["pedigree_coverage_era"] = ped_era

    (SCRATCH / "stage0_stats.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
