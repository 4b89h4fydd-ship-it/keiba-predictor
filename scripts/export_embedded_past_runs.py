#!/usr/bin/env python3
"""Export all embedded horse history evidence from MotherDuck into a local SQLite index.

Read-only on MotherDuck. Retains variants and provenance rather than guessing
a unique race_id from incomplete historical records. Not a training-label exporter.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

DAY_QUERY = """
SELECT race_id, CAST(snapshot_json AS VARCHAR)
FROM my_db.arvexq_analytics.race_snapshots
WHERE race_date = CAST(? AS DATE)
ORDER BY race_id
"""
DAYS_QUERY = """SELECT DISTINCT CAST(race_date AS VARCHAR)
FROM my_db.arvexq_analytics.race_snapshots ORDER BY 1"""


def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def history_entries(snapshot):
    horses = snapshot.get("horses") or []
    if not isinstance(horses, list):
        return
    for horse in horses:
        if not isinstance(horse, dict):
            continue
        horse_id = str(horse.get("id") or "")
        name = str(horse.get("name") or "").strip()
        if not horse_id and not name:
            continue
        # Do not merge allPastRuns and recentRaces without provenance: repeated
        # snapshots and disagreeing historical feeds may contain useful revisions.
        for source in ("allPastRuns", "recentRaces", "pastRaces", "history", "runs"):
            items = horse.get(source)
            if not isinstance(items, list):
                continue
            for run in items:
                if not isinstance(run, dict):
                    continue
                yield horse_id, name, source, run


def create_index(db):
    db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sources (
          race_id TEXT PRIMARY KEY, race_date TEXT NOT NULL, snapshot_sha TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS observations (
          race_id TEXT NOT NULL, horse_key TEXT NOT NULL, source TEXT NOT NULL,
          run_sha TEXT NOT NULL, run_date TEXT, track TEXT, title TEXT,
          payload TEXT NOT NULL,
          PRIMARY KEY(race_id,horse_key,source,run_sha)
        );
        CREATE INDEX IF NOT EXISTS idx_obs_date ON observations(run_date);
        CREATE INDEX IF NOT EXISTS idx_obs_horse ON observations(horse_key);
        CREATE VIEW IF NOT EXISTS distinct_run_evidence AS
          SELECT horse_key, run_sha, MIN(run_date) run_date,
                 MIN(track) track, MIN(title) title,
                 COUNT(*) observation_count
          FROM observations GROUP BY horse_key,run_sha;
    """)


def export(connection, db):
    create_index(db)
    for (day,) in connection.execute(DAYS_QUERY).fetchall():
        # Date-scoped access prevents a full database JSON materialization.
        cursor = connection.execute(DAY_QUERY, [day])
        while batch := cursor.fetchmany(1):
            for race_id, raw in batch:
                snapshot = json.loads(raw)
                if "帯広" in str(race_id) or snapshot.get("track") == "帯広":
                    continue
                db.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?)",
                           (race_id, day, fingerprint(snapshot)))
                for horse_id, name, source, run in history_entries(snapshot):
                    horse_key = horse_id or "name:" + name
                    payload = json.dumps(run, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":"))
                    db.execute("""INSERT OR IGNORE INTO observations
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (race_id, horse_key, source, fingerprint(run),
                         str(run.get("date") or run.get("raceDate") or ""),
                         str(run.get("track") or ""), str(run.get("title") or ""),
                         payload))
            db.commit()
    db.commit()
    counts = dict(db.execute("""SELECT
        (SELECT COUNT(*) FROM sources) AS source_races,
        (SELECT COUNT(*) FROM observations) AS observed_history_rows,
        (SELECT COUNT(*) FROM distinct_run_evidence) AS distinct_horse_run_payloads
    """).fetchone())
    return counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", default="md:my_db")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite historical index; choose a fresh output path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    import duckdb
    with duckdb.connect(args.database, read_only=True) as md:
        with sqlite3.connect(args.output) as out:
            out.row_factory = sqlite3.Row
            totals = export(md, out)
    # A distinct horse/run JSON payload is NOT automatically a distinct race,
    # and historical observations cannot be certified as preoff snapshots.
    manifest = {"role": "historical-feature-evidence-only",
                "source": "my_db.arvexq_analytics.race_snapshots",
                "future_information_warning": "Use only runs older than target date, with provenance checks",
                "unique_race_count": "unknown; historical run identities need reconciliation",
                "counts": totals}
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
