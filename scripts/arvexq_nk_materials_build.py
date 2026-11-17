#!/usr/bin/env python3
"""Build one date's production nk-materials file from the forward
collection outputs.

The publish lane (scripts/arvexq_rewrite_publish.py) reads
``rewrite/data/nk_materials/<date>.json`` — the transport that
carries the collected netkeiba materials into GitHub Actions,
in the same style as the v8 extras. This builder is the
normaliser between the collection side and that file; its inputs:

  --speed-index       speed-index.json from the forward
                      collection (per netkeiba race_id, per horse:
                      nk_best / nk_avg5 / nk_dist / nk_course /
                      nk_recent — the speed page's full columns)
  --course-analysis   course-analysis.json (per netkeiba race_id:
                      the course-analysis tables as collected)
  --targets           course-analysis-targets.json (the netkeiba
                      race_id <-> ARVEXQ race_id mapping)
  --race-details-dir  (optional, v2) a directory of per-race
                      detail JSONs named <arvexq_race_id>.json in
                      the production API's shape (either the full
                      response with a "detail" object or the detail
                      itself). Supplies each runner's past runs,
                      from which bestTime and headToHead are
                      computed with exactly the data-analysis
                      tab's definitions (see below).
  --horse-profiles    (optional, v2) the date's horse-profiles
                      JSON (arvexq-horse-profiles-v1: per netkeiba
                      horse_id: name / sire / dam / damSire /
                      siblings). Joined to runners by name (names
                      are unique within a date; a collision drops
                      the join rather than guessing).
  --newspaper         (optional, v2) per-horse newspaper marks in
                      the shape {"races": {<netkeiba race_id>:
                      {"horses": {<number>: <verbatim entry>}}}};
                      entries are carried through untouched as the
                      horse's "press" field.

Output format (version "nk-materials-v2"):

  {"version": "nk-materials-v2", "date": ..., "source": ...,
   "generatedAt": ...,
   "fieldCoverage": {<per-field horse counts over the file>},
   "races": {<arvexq_race_id>: {
       "netkeibaRaceId": <netkeiba race_id>,
       "horses": {<horse number as str>: {
           "nk_best": int|null, "nk_avg5": int|null,
           "nk_dist": int|null, "nk_course": int|null,
           "nk_recent": [int|null, ...] | null,
           "bestTime": {<the data-analysis tab's best-time pick:
               seconds, tier (1-4 in the tab's fallback order),
               track, surface, distance, date, finish,
               condition>} | null,
           "headToHead": {meetings, opponents, duels, ahead,
               aheadRate} | null,
           "pedigree": {sire, dam, damSire,
               "sireCourse": {starts, wins, top3, winRate} | null,
               "siblings": {count, wins} | null} | null,
           "press": <verbatim newspaper entry> | null}},
       "courseAnalysis": {<the collected course-analysis entry,
                           minus its arvexq_race_id echo>} | null}}}

Definitions (identical to the app's data-analysis tab, PR #564):

  bestTime — the runner's past runs are allPastRuns + recentRaces
  deduped on date|track|distance|raceId (first occurrence wins),
  restricted to runs with a positive timeSeconds; the pick is the
  fastest run in the first non-empty tier of (1) same track +
  same surface kind + same distance, (2) same track + same
  surface kind, (3) same surface kind anywhere, (4) any timed
  run. Surface kind: 芝… -> turf, ダ… -> dirt, else none.

  headToHead — two of today's runners met when their past runs
  share date + track + race number + distance (a run without a
  race number never joins; a key whose runs disagree on the race
  title is dropped as ambiguous). Per horse: meetings (shared
  races it ran in), opponents (distinct rivals met), duels
  (pairwise comparisons where both finishes are known), ahead
  (duels it finished in front), aheadRate = ahead / duels.

  pedigree.sireCourse — the horse's sire looked up in today's
  course-analysis sire table (得意な種牡馬, which is per venue +
  distance + surface): starts / wins / top-3 finishes and the
  win rate recomputed from those counts. A sire absent from the
  table has no course record — null, never estimated.

Rules: values are carried verbatim from the collection (nulls
stay null — a "-" / 未 cell is missing material, never imputed);
a race present in the targets but missing from a collection file
keeps the other file's data with the missing side null/empty; a
race in NO input file is omitted. Nothing is estimated. The v1
fields (speed columns, courseAnalysis) are produced exactly as
before; the v2 fields are additive and null whenever their input
was not supplied or the value does not exist.

Usage:
  python3 scripts/arvexq_nk_materials_build.py --date 2026-11-17 \
      --speed-index <path> --course-analysis <path> \
      --targets <path> [--race-details-dir <dir>] \
      [--horse-profiles <path>] [--newspaper <path>] \
      [--out rewrite/data/nk_materials/2026-11-17.json]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).resolve().parent.parent
SPEED_COLUMNS = ("nk_best", "nk_avg5", "nk_dist", "nk_course")
V2_HORSE_FIELDS = ("bestTime", "headToHead", "pedigree", "press")


# ------------------------------------------------------------------
# Past-run helpers (mirroring the data-analysis tab's definitions)
# ------------------------------------------------------------------

def _surface_kind(surface) -> str:
    s = str(surface or "")
    if s.startswith("芝"):
        return "turf"
    if s.startswith("ダ"):
        return "dirt"
    return ""


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _past_runs(horse: dict) -> list:
    """allPastRuns + recentRaces deduped on
    date|track|distance|raceId, first occurrence wins — the tab's
    pastRunsForDetail fallback merge."""
    seen: set = set()
    out: list = []
    runs = list(horse.get("allPastRuns") or []) + \
        list(horse.get("recentRaces") or [])
    for run in runs:
        if not isinstance(run, dict):
            continue
        key = (str(run.get("date") or ""), str(run.get("track") or ""),
               str(run.get("distance") or ""), str(run.get("raceId") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(run)
    return out


def _best_time(detail: dict, runs: list):
    """The tab's bestTimePick: fastest timed run in the first
    non-empty fallback tier; the winning run's own conditions are
    recorded so a fallback time is never mistaken for a
    same-course one."""
    timed = [r for r in runs if (_num(r.get("timeSeconds")) or 0) > 0]
    if not timed:
        return None
    kind = _surface_kind(detail.get("surface"))
    track = detail.get("track")
    dist = _num(detail.get("distance")) or 0

    def _best(candidates):
        return min(candidates, key=lambda r: r["timeSeconds"])

    tiers = [
        [r for r in timed if track and r.get("track") == track
         and (not kind or _surface_kind(r.get("surface")) == kind)
         and dist and (_num(r.get("distance")) or 0) == dist],
        [r for r in timed if track and r.get("track") == track
         and (not kind or _surface_kind(r.get("surface")) == kind)],
        [r for r in timed
         if not kind or _surface_kind(r.get("surface")) == kind],
        timed,
    ]
    for tier_no, candidates in enumerate(tiers, start=1):
        if not candidates:
            continue
        picked = _best(candidates)
        finish = _num(picked.get("finish"))
        return {
            "seconds": picked["timeSeconds"],
            "tier": tier_no,
            "track": picked.get("track"),
            "surface": picked.get("surface"),
            "distance": _num(picked.get("distance")),
            "date": picked.get("date"),
            "finish": int(finish) if finish else None,
            "condition": picked.get("condition"),
        }
    return None


def _head_to_head(runners: list) -> dict:
    """Meetings among today's runners, keyed exactly as the tab's
    headToHeadSection keys them. Returns {horse number: aggregate}
    for horses that met at least one opponent."""
    by_key: dict = {}
    for number, runs in runners:
        seen: set = set()
        for run in runs:
            race_no = _num(run.get("raceNumber")) or 0
            if not run.get("date") or not run.get("track") or not race_no:
                continue
            key = (str(run["date"]), str(run["track"]), race_no,
                   _num(run.get("distance")) or 0)
            if key in seen:
                continue
            seen.add(key)
            by_key.setdefault(key, []).append((number, run))
    aggregates: dict = {}
    for entries in by_key.values():
        if len(entries) < 2:
            continue
        titles = {str(r.get("title")) for _, r in entries if r.get("title")}
        if len(titles) > 1:
            continue  # ambiguous key — dropped, never guessed
        for number, run in entries:
            agg = aggregates.setdefault(number, {
                "meetings": 0, "opponents": set(), "duels": 0, "ahead": 0})
            agg["meetings"] += 1
            my_finish = _num(run.get("finish")) or 0
            for other, other_run in entries:
                if other == number:
                    continue
                agg["opponents"].add(other)
                other_finish = _num(other_run.get("finish")) or 0
                if my_finish > 0 and other_finish > 0:
                    agg["duels"] += 1
                    if my_finish < other_finish:
                        agg["ahead"] += 1
    out: dict = {}
    for number, agg in aggregates.items():
        duels = agg["duels"]
        out[number] = {
            "meetings": agg["meetings"],
            "opponents": len(agg["opponents"]),
            "duels": duels,
            "ahead": agg["ahead"],
            "aheadRate": round(agg["ahead"] / duels, 4) if duels else None,
        }
    return out


# ------------------------------------------------------------------
# Pedigree
# ------------------------------------------------------------------

def _profiles_by_name(profiles) -> dict:
    """{horse name: profile}; a name carried by two profiles is
    dropped (ambiguous join) rather than guessed."""
    horses = (profiles or {}).get("horses")
    if not isinstance(horses, dict):
        return {}
    by_name: dict = {}
    ambiguous: set = set()
    for profile in horses.values():
        if not isinstance(profile, dict):
            continue
        name = profile.get("name")
        if not name:
            continue
        if name in by_name:
            ambiguous.add(name)
        by_name[name] = profile
    for name in ambiguous:
        by_name.pop(name, None)
    return by_name


def _int_cell(value):
    """A count cell: ints pass through, pure-digit strings are
    converted (the Kanazawa collection arrived as strings), and
    anything else is not a count."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _sire_course(course_entry, sire):
    """The sire's record in today's course-analysis sire table
    (per venue + distance + surface). None when the table or the
    sire is absent — no record exists, nothing is estimated."""
    if not isinstance(course_entry, dict) or not sire:
        return None
    table = course_entry.get("得意な種牡馬")
    if not isinstance(table, dict):
        return None
    for row in table.get("行") or []:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        if str(row[0]) != str(sire):
            continue
        first = _int_cell(row[1])
        second = _int_cell(row[2])
        third = _int_cell(row[3])
        starts = _int_cell(row[5])
        if first is None or starts is None or starts <= 0:
            return None
        top3 = first + (second or 0) + (third or 0)
        return {"starts": starts, "wins": first, "top3": top3,
                "winRate": round(first / starts, 4)}
    return None


def _pedigree(profile, course_entry):
    if not isinstance(profile, dict):
        return None
    siblings = profile.get("siblings")
    sibling_summary = None
    if isinstance(siblings, list):
        wins = sum(w for w in
                   (_int_cell(s.get("wins")) if isinstance(s, dict)
                    else None for s in siblings) if w is not None)
        sibling_summary = {"count": len(siblings), "wins": wins}
    return {
        "sire": profile.get("sire"),
        "dam": profile.get("dam"),
        "damSire": profile.get("damSire"),
        "sireCourse": _sire_course(course_entry, profile.get("sire")),
        "siblings": sibling_summary,
    }


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------

def build(date: str, speed_index: dict, course_analysis: dict,
          targets: dict, race_details: dict | None = None,
          horse_profiles: dict | None = None,
          newspaper: dict | None = None) -> dict:
    speed_races = (speed_index.get("races")
                   if isinstance(speed_index, dict) else None) or {}
    profiles = _profiles_by_name(horse_profiles)
    press_races = (newspaper.get("races")
                   if isinstance(newspaper, dict) else None) or {}
    races: dict = {}
    for target in targets.get("targets") or []:
        nk_id = str(target.get("netkeiba_race_id") or "")
        aq_id = str(target.get("arvexq_race_id") or "")
        if not nk_id or not aq_id:
            continue
        speed_entry = speed_races.get(nk_id) or {}
        raw_horses = speed_entry.get("horses") or {}
        horses: dict = {}
        for key, values in raw_horses.items():
            if not isinstance(values, dict):
                continue
            horse = {col: values.get(col) for col in SPEED_COLUMNS}
            horse["nk_recent"] = values.get("nk_recent")
            horses[str(key)] = horse
        course = None
        raw_course = (course_analysis or {}).get(nk_id)
        if isinstance(raw_course, dict):
            course = {k: v for k, v in raw_course.items()
                      if k != "arvexq_race_id"}
        # --- v2 additions -------------------------------------
        detail = (race_details or {}).get(aq_id)
        press_horses = (press_races.get(nk_id) or {}).get("horses") or {}
        runners: list = []
        if isinstance(detail, dict):
            for runner in detail.get("horses") or []:
                if not isinstance(runner, dict):
                    continue
                number = runner.get("horseNumber")
                if not isinstance(number, int) or number <= 0:
                    continue
                if runner.get("scratched"):
                    continue  # not a runner today (the tab agrees)
                runners.append((number, runner, _past_runs(runner)))
        h2h = _head_to_head([(n, runs) for n, _, runs in runners]) \
            if runners else {}
        for number, runner, runs in runners:
            horse = horses.setdefault(str(number), {
                col: None for col in SPEED_COLUMNS} | {"nk_recent": None})
            horse["bestTime"] = _best_time(detail, runs)
            horse["headToHead"] = h2h.get(number)
            horse["pedigree"] = _pedigree(
                profiles.get(runner.get("name") or ""), course)
            press = press_horses.get(str(number))
            horse["press"] = press if isinstance(press, dict) else None
        # Every horse carries every v2 field; a horse the detail
        # input did not cover (or a race with no detail input at
        # all) gets uniform nulls — not collected, never zero.
        for horse in horses.values():
            for field in V2_HORSE_FIELDS:
                horse.setdefault(field, None)
        if not horses and course is None:
            continue
        races[aq_id] = {"netkeibaRaceId": nk_id, "horses": horses,
                        "courseAnalysis": course}
    coverage: dict = {}
    all_horses = [h for r in races.values() for h in r["horses"].values()]
    coverage["horses"] = len(all_horses)
    coverage["speed"] = sum(1 for h in all_horses
                            if h.get("nk_avg5") is not None)
    for field in V2_HORSE_FIELDS:
        coverage[field] = sum(1 for h in all_horses
                              if h.get(field) is not None)
    coverage["sireCourse"] = sum(
        1 for h in all_horses
        if isinstance(h.get("pedigree"), dict)
        and h["pedigree"].get("sireCourse") is not None)
    return {
        "version": "nk-materials-v2",
        "date": date,
        "source": "netkeiba-forward-collection",
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "fieldCoverage": coverage,
        "races": races,
    }


def load_race_details(directory) -> dict:
    """{arvexq_race_id: detail} from a directory of per-race
    detail JSONs. Accepts the API response shape ({"detail": ...})
    or a bare detail object; the race id is the detail's own id,
    falling back to the file name."""
    out: dict = {}
    if not directory:
        return out
    for path in sorted(Path(directory).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        detail = payload.get("detail") if isinstance(payload, dict) \
            else None
        if not isinstance(detail, dict):
            detail = payload if isinstance(payload, dict) else None
        if not isinstance(detail, dict) or "horses" not in detail:
            continue
        race_id = detail.get("id") or path.stem
        out[str(race_id)] = detail
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--speed-index", required=True)
    parser.add_argument("--course-analysis", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--race-details-dir")
    parser.add_argument("--horse-profiles")
    parser.add_argument("--newspaper")
    parser.add_argument("--out")
    args = parser.parse_args()

    def _load(path):
        if not path:
            return {}
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    payload = build(args.date, _load(args.speed_index),
                    _load(args.course_analysis), _load(args.targets),
                    race_details=load_race_details(args.race_details_dir),
                    horse_profiles=_load(args.horse_profiles),
                    newspaper=_load(args.newspaper))
    out = (Path(args.out) if args.out else
           ROOT / "rewrite" / "data" / "nk_materials" / f"{args.date}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    coverage = payload["fieldCoverage"]
    print(f"wrote {out}: {len(payload['races'])} races, "
          f"{coverage['horses']} horses, coverage={coverage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
