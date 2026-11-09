#!/usr/bin/env python3
"""Nankan win-odds time-series recorder (measurement infrastructure).

Usage:
  python scripts/arvexq_nankan_odds_record.py [<store_db>] [--samples N]
                                                 [--gap-seconds S]

Why this exists (yukochi-imitation plan, Phase 1 step 3): every
honest market comparison needs the odds AS THEY WERE at prediction
time. The production API's stored odds converge to the final odds,
which flattered every past backtest (the market-blend experiment's
own conclusion). yukochi's design records odds from about 40
minutes before the off at 2-minute intervals, timestamped, with
gaps left blank. This recorder is the ARVEXQ version for Nankan:

- Scope: today's Nankan races (大井・川崎・船橋・浦和, nar- ids).
- Window per race: T-45 .. T-3 minutes (after T-3 the recorded
  price is no longer a price anyone could act on pre-off).
- Each invocation samples immediately; with --samples > 1 it
  repeats every --gap-seconds while races remain in window, so a
  5-minute cron cadence still yields ~2-minute spacing in bursts.
- Append-only store with UPDATE/DELETE blocked by triggers.
  A missing odds value is stored as NULL — never interpolated,
  never back-filled from a later fetch.
- The Phase 0 audit store and odds_supplements are untouched;
  this is a separate series by design (plan.md Phase 1.3).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.data.sources import API_BASE, BROWSER_UA  # noqa: E402

NANKAN = {"大井", "川崎", "船橋", "浦和"}
JST = ZoneInfo("Asia/Tokyo")
WINDOW_OPEN_MIN = 45.0
WINDOW_CLOSE_MIN = 3.0
DEFAULT_STORE = "var/seals/odds_snapshots_nankan.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS odds_snapshots (
    race_id TEXT NOT NULL,
    race_date TEXT NOT NULL,
    track TEXT NOT NULL,
    horse_no INTEGER NOT NULL,
    win_odds REAL,
    popularity INTEGER,
    fetched_at TEXT NOT NULL,
    minutes_before REAL NOT NULL,
    source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_race
    ON odds_snapshots (race_id, fetched_at);
CREATE TRIGGER IF NOT EXISTS odds_snapshots_no_update
    BEFORE UPDATE ON odds_snapshots
    BEGIN SELECT RAISE(ABORT, 'odds snapshots are append-only'); END;
CREATE TRIGGER IF NOT EXISTS odds_snapshots_no_delete
    BEFORE DELETE ON odds_snapshots
    BEGIN SELECT RAISE(ABORT, 'odds snapshots are append-only'); END;
CREATE TABLE IF NOT EXISTS record_runs (
    ran_at TEXT NOT NULL,
    races_in_window INTEGER NOT NULL,
    rows_written INTEGER NOT NULL,
    note TEXT
);
"""


def http_get_json(path: str, timeout: float = 25.0) -> dict:
    request = urllib.request.Request(
        f"{API_BASE}{path}", headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def scheduled_dt(race_date: str, start_time: str) -> datetime | None:
    try:
        return datetime.fromisoformat(
            f"{race_date}T{start_time}:00").replace(tzinfo=JST)
    except Exception:
        return None


def todays_nankan(now_jst: datetime) -> list[dict]:
    payload = http_get_json(
        f"/api/races?date={urllib.parse.quote(now_jst.date().isoformat())}")
    out = []
    for race in payload.get("races") or []:
        race_id = race.get("race_id") or ""
        if not race_id.startswith("nar-"):
            continue
        if race.get("track") not in NANKAN:
            continue
        start = scheduled_dt(race.get("race_date") or "", race.get("start_time") or "")
        if start is None:
            continue
        out.append({"race_id": race_id, "race_date": race.get("race_date"),
                    "track": race.get("track"), "start": start})
    return out


def sample_once(db: sqlite3.Connection, races: list[dict],
                now_jst: datetime) -> tuple[int, int]:
    """Fetch each in-window race once and append its odds rows."""
    in_window = []
    for race in races:
        minutes = (race["start"] - now_jst).total_seconds() / 60.0
        if WINDOW_CLOSE_MIN <= minutes <= WINDOW_OPEN_MIN:
            in_window.append((race, minutes))
    rows = 0
    for race, minutes in in_window:
        payload = http_get_json(
            f"/api/race/{urllib.parse.quote(race['race_id'], safe='')}")
        detail = payload.get("detail") or {}
        odds_by_no = {}
        for row in payload.get("odds") or []:
            if isinstance(row, dict) and row.get("horse_no") is not None:
                odds_by_no[row["horse_no"]] = row
        fetched_at = datetime.now(timezone.utc).isoformat()
        batch = []
        for horse in detail.get("horses") or []:
            no = horse.get("horseNumber")
            if no is None:
                continue
            orow = odds_by_no.get(no, {})
            win_odds = horse.get("winOdds")
            if win_odds in (None, "", 0):
                win_odds = orow.get("win_odds")
            popularity = horse.get("popularity")
            if popularity in (None, "", 0):
                popularity = orow.get("popularity")
            batch.append((
                race["race_id"], race["race_date"], race["track"], int(no),
                float(win_odds) if isinstance(win_odds, (int, float)) else None,
                int(popularity) if isinstance(popularity, (int, float)) else None,
                fetched_at, round(minutes, 2), "production-api-detail",
            ))
        db.executemany(
            "INSERT INTO odds_snapshots (race_id, race_date, track, "
            "horse_no, win_odds, popularity, fetched_at, minutes_before, "
            "source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
        rows += len(batch)
    db.commit()
    return len(in_window), rows


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("store", nargs="?", default=DEFAULT_STORE)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--gap-seconds", type=float, default=120.0)
    parsed = parser.parse_args()
    samples = parsed.samples
    gap = parsed.gap_seconds
    store_path = Path(parsed.store)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(store_path))
    db.executescript(SCHEMA)
    total_races = total_rows = 0
    note = None
    try:
        races = todays_nankan(datetime.now(JST))
        for i in range(max(1, samples)):
            if i:
                time.sleep(gap)
            now_jst = datetime.now(JST)
            n_races, n_rows = sample_once(db, races, now_jst)
            total_races = max(total_races, n_races)
            total_rows += n_rows
            if n_races == 0:
                break
    except Exception as exc:
        note = f"error: {str(exc)[:200]}"
        db.execute(
            "INSERT INTO record_runs VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), total_races,
             total_rows, note))
        db.commit()
        print(json.dumps({"status": "error", "error": note},
                         ensure_ascii=False))
        return 1
    finally:
        db.close()
    print(json.dumps({
        "status": "ok", "races_in_window": total_races,
        "rows_written": total_rows, "store": str(store_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
