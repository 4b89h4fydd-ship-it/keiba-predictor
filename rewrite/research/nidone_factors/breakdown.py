"""Stage-4 breakdowns + failure-race analysis from the primary
pair CSVs: honmei flips, venue / distance / field-size splits."""
from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def load_csv(name):
    with open(common.SCRATCH / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def flips(rows):
    f = {"flips": 0, "base_only": 0, "cand_only": 0, "both_lost": 0,
         "same": 0}
    for r in rows:
        if r["base_honmei"] == r["cand_honmei"]:
            f["same"] += 1
            continue
        f["flips"] += 1
        bw = str(r["base_honmei"]) == str(r["winner"])
        cw = str(r["cand_honmei"]) == str(r["winner"])
        if bw and not cw:
            f["base_only"] += 1
        elif cw and not bw:
            f["cand_only"] += 1
        else:
            f["both_lost"] += 1
    return f


def split_diffs(rows, keyfn):
    agg = defaultdict(lambda: [0, 0.0, 0.0])
    for r in rows:
        k = keyfn(r)
        if k is None:
            continue
        bw = 1.0 if str(r["base_honmei"]) == str(r["winner"]) else 0.0
        cw = 1.0 if str(r["cand_honmei"]) == str(r["winner"]) else 0.0
        agg[k][0] += 1
        agg[k][1] += bw
        agg[k][2] += cw
    return {k: {"races": v[0], "base_honmei_rate": round(v[1] / v[0], 3),
                "cand_honmei_rate": round(v[2] / v[0], 3),
                "diff": round((v[2] - v[1]) / v[0], 4)}
            for k, v in sorted(agg.items())}


def main() -> int:
    db = common.corpus()
    meta = {r[0]: (r[1], r[2]) for r in db.execute(
        "SELECT race_id, distance, (SELECT COUNT(*) FROM runners"
        " WHERE runners.race_id = races.race_id) FROM races")}
    out = {}
    for name, label in (("m1_primary_pairs_nar.csv", "m1_nar"),
                        ("m1_primary_pairs_jra.csv", "m1_jra"),
                        ("m2_primary_pairs_nar_fixed.csv", "m2_fixed_nar"),
                        ("m2_primary_pairs_nar_decay.csv", "m2_decay_nar")):
        rows = load_csv(name)
        out[label] = {
            "flips": flips(rows),
            "by_venue": split_diffs(rows, lambda r: r["race_id"].split("-")[4]),
            "by_distance": split_diffs(
                rows, lambda r: ("<=1400" if meta.get(r["race_id"], (0, 0))[0] <= 1400
                                 else "1401-1800" if meta.get(r["race_id"], (0, 0))[0] <= 1800
                                 else "1801+") if meta.get(r["race_id"]) else None),
            "by_field": split_diffs(
                rows, lambda r: ("<=10" if meta.get(r["race_id"], (0, 0))[1] <= 10
                                 else "11-14" if meta.get(r["race_id"], (0, 0))[1] <= 14
                                 else "15+") if meta.get(r["race_id"]) else None),
            "by_year": split_diffs(rows, lambda r: r["date"][:4]),
        }
    (common.SCRATCH / "breakdown.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
