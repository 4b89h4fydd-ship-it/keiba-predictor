"""NIDONE-factor research corpus builder (2026-11-09).

One pass over every canonical day DB (pm_common.db_path_for_date rule:
pool DBs for the pool era, material-pin-aware day DBs for the live era)
extracting a light, research-only corpus:

  races     - one row per normalized race (meta only)
  runners   - one row per card runner (identity + frame + odds)
  past_runs - one row per past-run record on a card, owned by the
              runner's natkey (name|sex|birth_year, pipeline format
              "name:<name>|<sex>|<year>")
  pedigree  - horse_pedigree rows copied verbatim (provenance kept)

Nothing here writes to any production or seal store.  Output is a
single sqlite file under var/scratch/nidone-factors-20261109/.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "var" / "scratch" / "past-market-20261108"))

import pm_common  # noqa: E402

OUT = PROJECT / "var" / "scratch" / "nidone-factors-20261109" / "corpus.sqlite3"
FIRST = date(2025, 12, 23)
LAST = date(2026, 11, 9)


def val(node):
    if isinstance(node, dict):
        return node.get("value")
    return node


def natkey(name, sex, birth_year):
    if name is None or sex is None or birth_year is None:
        return None
    return f"name:{name}|{sex}|{birth_year}"


def main() -> int:
    if OUT.exists():
        OUT.unlink()
    out = sqlite3.connect(OUT)
    out.executescript(
        """
        CREATE TABLE races (
          race_id TEXT PRIMARY KEY, race_date TEXT, box TEXT, track TEXT,
          race_number INTEGER, distance INTEGER, surface TEXT,
          condition TEXT, segment TEXT, start_time TEXT, title TEXT,
          n_runners INTEGER, db_date TEXT);
        CREATE TABLE runners (
          race_id TEXT, number INTEGER, name TEXT, sex TEXT, age INTEGER,
          birth_year INTEGER, natkey TEXT, frame INTEGER,
          win_odds REAL, scratched INTEGER,
          PRIMARY KEY (race_id, number));
        CREATE TABLE past_runs (
          owner_natkey TEXT, owner_name TEXT, card_race_id TEXT,
          run_date TEXT, track TEXT, race_number INTEGER,
          finish INTEGER, field_size INTEGER, margin_seconds REAL,
          time_behind REAL, distance INTEGER, surface TEXT,
          corner_first REAL, corner_last REAL, race_title TEXT,
          did_not_run INTEGER);
        CREATE INDEX idx_pr_owner ON past_runs(owner_natkey);
        CREATE INDEX idx_pr_key ON past_runs(run_date, track, race_number);
        CREATE TABLE pedigree (
          race_id TEXT, race_date TEXT, circuit TEXT, track TEXT,
          race_no INTEGER, horse_number INTEGER, horse_name TEXT,
          sex TEXT, birth_year INTEGER, natkey TEXT, sire TEXT,
          dam TEXT, damsire TEXT, source TEXT, fetched_at TEXT,
          PRIMARY KEY (race_id, horse_number));
        """
    )
    stats = {"dbs": 0, "races": 0, "runners": 0, "past_runs": 0, "pedigree": 0,
             "missing_db": []}
    d = FIRST
    while d <= LAST:
        ds = d.isoformat()
        path = pm_common.db_path_for_date(ds)
        if path is None or not Path(path).exists():
            stats["missing_db"].append(ds)
            d += timedelta(days=1)
            continue
        stats["dbs"] += 1
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = db.execute(
                "SELECT race_id, normalized_json FROM normalized_races"
            ).fetchall()
        except sqlite3.Error:
            rows = []
        for race_id, body in rows:
            try:
                p = json.loads(body)
            except Exception:
                continue
            rdate = p.get("date") or ds
            box = "jra" if str(race_id).startswith("jra-") else "nar"
            track = p.get("track")
            rnum = val(p.get("race_number"))
            runners = p.get("runners") or []
            out.execute(
                "INSERT OR REPLACE INTO races VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (race_id, rdate, box, track,
                 int(rnum) if rnum is not None else None,
                 val(p.get("distance")), val(p.get("surface")),
                 val(p.get("condition")), p.get("segment"),
                 val(p.get("start_time")), val(p.get("title")),
                 len(runners), ds))
            stats["races"] += 1
            year = int(str(rdate)[:4])
            for r in runners:
                name = val(r.get("name"))
                sex = val(r.get("sex"))
                age = val(r.get("age"))
                by = (year - int(age)) if isinstance(age, (int, float)) else None
                nk = natkey(name, sex, by)
                odds = val(r.get("win_odds"))
                out.execute(
                    "INSERT OR REPLACE INTO runners VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (race_id, r.get("number"), name, sex,
                     int(age) if isinstance(age, (int, float)) else None,
                     by, nk, val(r.get("frame_number")),
                     float(odds) if isinstance(odds, (int, float)) else None,
                     1 if r.get("scratched") else 0))
                stats["runners"] += 1
                for pr in r.get("past_runs") or []:
                    corners = pr.get("corner_positions") or []
                    out.execute(
                        "INSERT INTO past_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (nk, name, race_id, pr.get("date"),
                         val(pr.get("track")),
                         val(pr.get("race_number")),
                         val(pr.get("finish")), val(pr.get("field_size")),
                         val(pr.get("margin_seconds")),
                         val(pr.get("time_behind_winner")),
                         val(pr.get("distance")), val(pr.get("surface")),
                         float(corners[0]) if corners else None,
                         float(corners[-1]) if len(corners) > 1 else
                         (float(corners[0]) if corners else None),
                         val(pr.get("race_title")),
                         1 if pr.get("did_not_run") else 0))
                    stats["past_runs"] += 1
        try:
            ped = db.execute(
                "SELECT race_id, race_date, circuit, track, race_no,"
                " horse_number, horse_name, sex, birth_year, natkey,"
                " sire, dam, damsire, source, fetched_at"
                " FROM horse_pedigree").fetchall()
        except sqlite3.Error:
            ped = []
        for row in ped:
            out.execute(
                "INSERT OR REPLACE INTO pedigree VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(row))
            stats["pedigree"] += 1
        db.close()
        out.commit()
        d += timedelta(days=1)
    out.commit()
    print(json.dumps(stats, ensure_ascii=False))
    out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
