"""Supplement corpus pedigree from the plain ingest day DBs.

The material-pin copies used for forecast regeneration predate the
pedigree backfill, so their horse_pedigree tables are empty for most
live-era dates.  Pedigree names are static reference data harvested
from official cards (not forecast material), so the corpus takes the
union of both copies and audits that shared keys agree.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
CORPUS = PROJECT / "var" / "scratch" / "nidone-factors-20261109" / "corpus.sqlite3"

db = sqlite3.connect(CORPUS)
before = db.execute("SELECT count(*) FROM pedigree").fetchone()[0]
added = conflict = 0
d = date(2025, 12, 23)
while d <= date(2026, 11, 9):
    ds = d.isoformat()
    plain = PROJECT / "var" / f"rewrite-{ds}.sqlite3"
    if plain.exists():
        src = sqlite3.connect(f"file:{plain}?mode=ro", uri=True)
        try:
            rows = src.execute(
                "SELECT race_id, race_date, circuit, track, race_no,"
                " horse_number, horse_name, sex, birth_year, natkey,"
                " sire, dam, damsire, source, fetched_at FROM horse_pedigree"
            ).fetchall()
        except sqlite3.Error:
            rows = []
        src.close()
        for row in rows:
            cur = db.execute(
                "SELECT sire, dam, damsire FROM pedigree"
                " WHERE race_id=? AND horse_number=?", (row[0], row[5])).fetchone()
            if cur is None:
                db.execute(
                    "INSERT OR REPLACE INTO pedigree VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tuple(row))
                added += 1
            elif tuple(cur) != (row[10], row[11], row[12]):
                conflict += 1
    d += timedelta(days=1)
db.commit()
after = db.execute("SELECT count(*) FROM pedigree").fetchone()[0]
print({"before": before, "added": added, "after": after, "conflicts": conflict})
db.close()
