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
  --pace-forecast     (optional, v4) the forward collection's
                      pace-forecast.json (arvexq-pace-forecast-v1:
                      per netkeiba race_id: "pace" label (H/M/S)
                      and "positions" — the AI pace forecast's
                      start / corner3 / corner4 group diagrams,
                      each a list of groups of horse numbers from
                      the forecast front to the back). Converted
                      per horse to forecast position rank (1 =
                      forecast front) and percentile (rank /
                      field size) per phase, carried as the
                      horse's "pace" field; the race's label is
                      carried as the entry's "paceLabel".
  --nk-judgements     (optional, v6) per-horse netkeiba
                      judgements in the shape {"races":
                      {<netkeiba race_id>: {"horses":
                      {<number>: {"nkFormDev": <number>,
                      "nkAiScore": <number>}}}}}; the two values
                      are carried verbatim per horse as the
                      "nkFormDev" / "nkAiScore" fields. NO
                      forward collection produces this file yet
                      (the judgements live on JRA-side pages;
                      the 2026-11-17/18 collections are NAR days)
                      — the input exists so the values flow the
                      moment a collection saves them.
  --odds              (optional, v6) per-horse odds snapshots.
                      Two collected shapes are accepted (see
                      _normalise_odds_races): the dict shape
                      {"races": {<netkeiba race_id>: {"horses":
                      {<number>: {"publishWin": ..., "finalWin":
                      ..., "placeLow": ..., "placeHigh": ...}}}}}
                      (the 2026-11-18 collection's shape, produced
                      from the actual odds pages), and the list
                      shape {"races": {<netkeiba race_id>:
                      {"kind": ..., "horses": [{"no": ...,
                      "win_odds": ..., "place_min": ...,
                      "place_max": ...}]}}} (the 2026-11-19
                      collection's shape). Provenance is never
                      blurred: a "forecast" race's win line is
                      netkeiba's published forecast odds and is
                      carried as "forecastWin" only — it is NOT
                      promoted to finalWin (the market's actual
                      odds), so the odds-movement terms keep
                      yesterday's definitions and simply stay
                      unlit on a forecast-only file.
  --horse-analysis    (optional, 2026-11-19) the forward
                      collection's per-horse data-analysis
                      judgements (horse-analysis.json:
                      {"races": {<netkeiba race_id>: {"horses":
                      {<number>: {"総合評価": <grade>, <section>:
                      {"判定": <mark>, ...}}}}}}). Only the
                      judgements are carried — the overall grade
                      and each section's 判定, verbatim, as the
                      horse's "horseAnalysis" block
                      ({"overall": ..., "sections": {<section>:
                      <mark>}}); the sections' inner tables
                      restate the course aggregates and the
                      horse's own past runs, which reach the
                      file through the other inputs already.
  --course-persons    (optional, 2026-11-19) the forward
                      collection's course-persons.json (the
                      course-analysis persons tables — 得意な
                      騎手・調教師・種牡馬 — as per-entered-horse
                      rows). Its sire rows are a FALLBACK source
                      for pedigree.sireCourse when the race's
                      course entry carries no full sire table
                      (得意な種牡馬): the row is the same
                      course's record for the horse's own sire,
                      collected per horse, so the conversion is
                      a reshape, never an estimate. The full
                      table's record wins whenever both exist.
                      The jockey / trainer rows are carried as
                      each horse's "coursePersons" block
                      ({"jockey": {...}, "trainer": {...}} —
                      the person's name and course record) for
                      the adapter's course-persons trial terms
                      (nk-materials-v10); same-shaped rows on
                      the course-analysis race entry itself are
                      read as a second source, with this file
                      winning on a duplicate.

Output format (version "nk-materials-v10"):

  {"version": "nk-materials-v10", "date": ..., "source": ...,
   "generatedAt": ...,
   "fieldCoverage": {<per-field horse counts over the file>},
   "zeroCoverage": [<names of the expected fields whose count
                    is 0 — the uncollected list, on the record
                    in the file itself and in the build log, so
                    a zero can never pass silently>],
   "races": {<arvexq_race_id>: {
       "netkeibaRaceId": <netkeiba race_id>,
       "paceLabel": <"H"|"M"|"S"|null>,
       "horses": {<horse number as str>: {
           "nk_best": int|null, "nk_avg5": int|null,
           "nk_dist": int|null, "nk_course": int|null,
           "nk_recent": [int|null, ...] | null,
           "nk_recent5": [int|null, ...] | null,
           "nkFormDev": number|null, "nkAiScore": number|null,
           "odds": {"publishWin": number|null,
                    "finalWin": number|null,
                    "placeLow": number|null,
                    "placeHigh": number|null,
                    "forecastWin": number (present only when
                    the collection carried netkeiba's forecast
                    win odds for the horse)} | null,
           "horseAnalysis": {"overall": <grade str>|null,
                    "sections": {<section>: <mark str>}} | null,
           "pace": {"start": {"rank": int, "pct": float},
                    "corner3": {...}, "corner4": {...}} | null,
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
  The v3 label also marks the adjustment definition that
  consumes the file (the course-analysis tables feed the
  weighted course terms: NAR at its fit+calib-selected
  weights, JRA at the same weights as a trial; see
  rewrite/analysis/nk_materials.py). The v4 label adds the
  pace fields above: the AI pace forecast's per-horse
  positions feed the adapter's pace term — a TRIAL term,
  UNVALIDATED because no historical pace-forecast data
  exists to validate against (the diagrams are published
  only around race day). The v6 label adds the nkFormDev /
  nkAiScore / odds fields above (null until a collection
  supplies them) and the derived-speed coverage counts in
  fieldCoverage (speedSlope / speedDev / speedVol / speedSd /
  speedOverlap / speedFit / speedBias — how many horses the
  adapter's v6 speed-derived terms can stand on, computed
  with integrated_eval's own feature functions from the raw
  columns; the derivation itself stays inside integrate(), so
  no derived values are duplicated into this file). The
  publish lane's parser does not gate on the version string,
  so v1/v2/v3 files load the same (their horses simply carry
  no pace field).

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
      [--pace-forecast <path>] \
      [--out rewrite/data/nk_materials/2026-11-17.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rewrite.analysis.integrated_eval import (  # noqa: E402
    band_overlap_share, speed_aptitude_features,
    speed_trend_features)

SPEED_COLUMNS = ("nk_best", "nk_avg5", "nk_dist", "nk_course")
V2_HORSE_FIELDS = ("bestTime", "headToHead", "pedigree", "press")
V6_HORSE_FIELDS = ("nkFormDev", "nkAiScore", "odds")
ODDS_CELLS = ("publishWin", "finalWin", "placeLow", "placeHigh")
PACE_PHASES = ("start", "corner3", "corner4")


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
# Pace forecast (v4)
# ------------------------------------------------------------------

def _pace_positions(pace_entry) -> tuple:
    """({horse number as str: {phase: {"rank", "pct"}}}, label)
    from one race's pace-forecast entry. Rank runs sequentially
    through the phase's groups from the forecast front (group
    order, then order within the group); pct = rank / field
    size, the field size being the phase's own horse count. A
    phase that is missing or malformed is simply absent; a
    horse absent from a phase carries no cell for it. Nothing
    is estimated — a group diagram that does not cover the
    field is carried as-is."""
    if not isinstance(pace_entry, dict):
        return {}, None
    positions = pace_entry.get("positions")
    if not isinstance(positions, dict):
        return {}, None
    label = pace_entry.get("pace")
    out: dict = {}
    for phase in PACE_PHASES:
        groups = positions.get(phase)
        if not isinstance(groups, list):
            continue
        flat: list = []
        for group in groups:
            if not isinstance(group, list):
                continue
            for number in group:
                if isinstance(number, int) and not isinstance(number, bool):
                    flat.append(number)
        if not flat:
            continue
        size = len(flat)
        for rank, number in enumerate(flat, start=1):
            out.setdefault(str(number), {})[phase] = {
                "rank": rank, "pct": round(rank / size, 4)}
    return out, (label if isinstance(label, str) else None)


# ------------------------------------------------------------------
# Odds normalisation (2026-11-19: the second collected shape)
# ------------------------------------------------------------------

def _normalise_odds_races(odds) -> dict:
    """{netkeiba race_id: {horse number as str: odds cells}} from
    either collected odds shape (see the module docstring).

    The dict shape (2026-11-18) passes its four cells through
    verbatim. The list shape (2026-11-19) is converted by the
    race's own "kind" label, which is the collection's
    provenance statement:

      "actual"      the values are the market's actual odds as
                    read from the odds page: win_odds ->
                    finalWin, place_min / place_max -> placeLow
                    / placeHigh (exactly the cells the dict
                    shape carries from the same pages).
      "forecast"    the values are netkeiba's published
                    FORECAST odds: the win line is carried as
                    forecastWin under its own name and the place
                    range is not carried at all — none of it may
                    wear the actual-odds cells' names.
      "actual_zero" the odds page showed 0.0 for every horse
                    (not yet published): no data, nothing carried.
      anything else an unlabelled list is treated like
                    "forecast" — unknown provenance is never
                    promoted to actual odds.

    A win line of 0.0 is "not published", never an odds value,
    in every shape. Cells a race cannot supply stay absent, so
    the odds-movement features keep their definitions and a
    forecast-only file lights neither of them."""
    races = (odds.get("races") if isinstance(odds, dict)
             else None) or {}
    out: dict = {}
    for nk_id, entry in races.items():
        if not isinstance(entry, dict):
            continue
        raw = entry.get("horses")
        cells_by_number: dict = {}
        if isinstance(raw, dict):
            for key, values in raw.items():
                if not isinstance(values, dict):
                    continue
                cells = {c: _num(values.get(c)) for c in ODDS_CELLS}
                forecast = _num(values.get("forecastWin"))
                if forecast is not None:
                    cells["forecastWin"] = forecast
                if any(v is not None for v in cells.values()):
                    cells_by_number[str(key)] = cells
        elif isinstance(raw, list):
            kind = entry.get("kind")
            for row in raw:
                if not isinstance(row, dict):
                    continue
                number = row.get("no")
                if not isinstance(number, int) \
                        or isinstance(number, bool):
                    continue
                win = _num(row.get("win_odds"))
                if win is not None and win <= 0:
                    win = None  # 0.0 = not published, not odds
                cells: dict = {}
                if kind == "actual":
                    if win is not None:
                        cells["finalWin"] = win
                    low = _num(row.get("place_min"))
                    high = _num(row.get("place_max"))
                    if low is not None and low > 0:
                        cells["placeLow"] = low
                    if high is not None and high > 0:
                        cells["placeHigh"] = high
                elif kind == "actual_zero":
                    pass  # the page showed 0.0 throughout: no data
                else:
                    if win is not None:
                        cells["forecastWin"] = win
                if cells:
                    cells_by_number[str(number)] = cells
        if cells_by_number:
            out[str(nk_id)] = cells_by_number
    return out


# ------------------------------------------------------------------
# Horse analysis (each horse's data-analysis judgements, 2026-11-19)
# ------------------------------------------------------------------

def _horse_analysis_block(entry):
    """{"overall": grade|None, "sections": {section: mark}} from
    one horse's collected horse-analysis entry: the overall
    grade (総合評価) and each section's judgement (判定),
    verbatim. A section is any dict-valued key carrying a 判定 —
    the section set is the page's, not a hardcoded list. The
    sections' inner tables are not carried (see the module
    docstring). None when the entry carries no readable
    judgement at all."""
    if not isinstance(entry, dict):
        return None
    overall = entry.get("総合評価")
    if not isinstance(overall, str) or not overall:
        overall = None
    sections: dict = {}
    for name, section in entry.items():
        if not isinstance(section, dict):
            continue
        mark = section.get("判定")
        if isinstance(mark, str) and mark:
            sections[name] = mark
    if overall is None and not sections:
        return None
    return {"overall": overall, "sections": sections}


# ------------------------------------------------------------------
# Course persons (sire-row fallback for sireCourse; jockey /
# trainer rows for the course-persons terms, 2026-11-19)
# ------------------------------------------------------------------


def _person_record(row):
    """{"name", "starts", "wins", "top3", "winRate"} from one
    course-persons row — the page's counts (past-3-years window,
    as the page states) for that person at today's course, in
    the same counts the full persons tables carry. A row whose
    counts cannot be read is dropped, never repaired."""
    if not isinstance(row, dict):
        return None
    finishes = row.get("finishes")
    starts = _int_cell(row.get("starts"))
    if not isinstance(finishes, dict) \
            or starts is None or starts <= 0:
        return None
    first = _int_cell(finishes.get("1st"))
    second = _int_cell(finishes.get("2nd"))
    third = _int_cell(finishes.get("3rd"))
    if first is None:
        return None
    return {"name": row.get("name"), "starts": starts,
            "wins": first,
            "top3": first + (second or 0) + (third or 0),
            "winRate": round(first / starts, 4)}


def _persons_kind_index(course_persons, course_analysis, kind):
    """{(netkeiba race_id, horse number as str): record} for
    one persons kind ("jockeys" / "trainers") from the
    course-persons collection's per-horse rows. The
    course-analysis race entry's own same-shaped rows (a
    collection may store them there instead) are a second
    source; the dedicated course-persons file wins on a
    duplicate."""
    out: dict = {}
    for source in (course_analysis, course_persons):
        races = (source.get("races")
                 if isinstance(source, dict) else None)
        if not isinstance(races, dict):
            # course_analysis is keyed by race id directly.
            races = source if isinstance(source, dict) else {}
        for nk_id, entry in races.items():
            if not isinstance(entry, dict):
                continue
            for row in entry.get(kind) or []:
                if not isinstance(row, dict):
                    continue
                number = row.get("no")
                if not isinstance(number, int) \
                        or isinstance(number, bool):
                    continue
                record = _person_record(row)
                if record is not None:
                    out[(str(nk_id), str(number))] = record
    return out

def _persons_sire_index(course_persons) -> dict:
    """{(netkeiba race_id, horse number as str): {"sire": name,
    "sireCourse": {starts, wins, top3, winRate}}} from the
    course-persons collection's per-horse sire rows — each row
    is today's course's record (past-3-years window, as the
    page states) for that horse's own sire, in the same counts
    the full sire table （得意な種牡馬） carries. A row whose
    counts cannot be read is dropped, never repaired."""
    races = (course_persons.get("races")
             if isinstance(course_persons, dict) else None) or {}
    out: dict = {}
    for nk_id, entry in races.items():
        if not isinstance(entry, dict):
            continue
        for row in entry.get("sires") or []:
            if not isinstance(row, dict):
                continue
            number = row.get("no")
            finishes = row.get("finishes")
            starts = _int_cell(row.get("starts"))
            if not isinstance(number, int) \
                    or isinstance(number, bool):
                continue
            if not isinstance(finishes, dict) \
                    or starts is None or starts <= 0:
                continue
            first = _int_cell(finishes.get("1st"))
            second = _int_cell(finishes.get("2nd"))
            third = _int_cell(finishes.get("3rd"))
            if first is None:
                continue
            out[(str(nk_id), str(number))] = {
                "sire": row.get("name"),
                "sireCourse": {
                    "starts": starts, "wins": first,
                    "top3": first + (second or 0) + (third or 0),
                    "winRate": round(first / starts, 4)}}
    return out


# ------------------------------------------------------------------
# Derived-speed coverage (v6)
# ------------------------------------------------------------------

def _derived_coverage(race_horses: list) -> dict:
    """Per-field horse counts for the adapter's v6 speed-derived
    terms, computed with integrated_eval's own feature functions
    over the same sanitised inputs integrate() will see (the
    publish parser's _num view of the raw columns). The counts
    answer "how many horses can this term stand on" at build
    time; the derivation itself stays inside integrate()."""
    trends = []
    for h in race_horses:
        recent = h.get("nk_recent")
        recent = ([_num(v) for v in recent]
                  if isinstance(recent, list) else None)
        trends.append(speed_trend_features(
            recent, _num(h.get("nk_avg5")), _num(h.get("nk_best"))))
    apts = [speed_aptitude_features(
        _num(h.get("nk_dist")), _num(h.get("nk_course")),
        t["last"], _num(h.get("nk_avg5")))
        for h, t in zip(race_horses, trends)]
    overlap = band_overlap_share([
        (t["mean_recent"], t["sd"])
        if t["mean_recent"] is not None and t["sd"] is not None
        else None for t in trends])
    return {
        "speedSlope": sum(1 for t in trends if t["slope"] is not None),
        "speedDev": sum(1 for t in trends
                        if t["last_minus_avg5"] is not None),
        "speedVol": sum(1 for t in trends if t["vol"] is not None),
        "speedSd": sum(1 for t in trends if t["sd"] is not None),
        "speedOverlap": sum(1 for v in overlap if v is not None),
        "speedFit": sum(1 for a in apts if a["fit_edge"] is not None),
        "speedBias": sum(1 for a in apts
                         if a["course_minus_dist"] is not None),
    }


# ------------------------------------------------------------------
# Build
# ------------------------------------------------------------------

def build(date: str, speed_index: dict, course_analysis: dict,
          targets: dict, race_details: dict | None = None,
          horse_profiles: dict | None = None,
          newspaper: dict | None = None,
          pace_forecast: dict | None = None,
          nk_judgements: dict | None = None,
          odds: dict | None = None,
          horse_analysis: dict | None = None,
          course_persons: dict | None = None) -> dict:
    speed_races = (speed_index.get("races")
                   if isinstance(speed_index, dict) else None) or {}
    profiles = _profiles_by_name(horse_profiles)
    press_races = (newspaper.get("races")
                   if isinstance(newspaper, dict) else None) or {}
    pace_races = (pace_forecast.get("races")
                  if isinstance(pace_forecast, dict) else None) or {}
    judgement_races = (nk_judgements.get("races")
                       if isinstance(nk_judgements, dict)
                       else None) or {}
    odds_races = _normalise_odds_races(odds)
    analysis_races = (horse_analysis.get("races")
                      if isinstance(horse_analysis, dict)
                      else None) or {}
    persons_sires = _persons_sire_index(course_persons)
    persons_jockeys = _persons_kind_index(
        course_persons, course_analysis, "jockeys")
    persons_trainers = _persons_kind_index(
        course_persons, course_analysis, "trainers")
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
            # nk-materials-v8 (2026-11-19, user instruction: put ALL
            # of the collected data into the forecast): when the
            # collection carries the 5-run sequence (nk_recent5,
            # oldest -> newest, from the speed page's 近5走 view),
            # the derived-feature window widens to it — nk_recent
            # carries the 5-run sequence and nk_recent5 keeps the
            # provenance. Horses without it keep the 3-run sequence.
            # Weights are unchanged from v7; only the input window
            # of the speed-derived features (slope / vol / sd /
            # overlap) widens. Trial adoption, unvalidated (no
            # historical 5-run corpus exists to validate against).
            recent5 = values.get("nk_recent5")
            horse["nk_recent"] = (recent5 if recent5
                                  else values.get("nk_recent"))
            horse["nk_recent5"] = recent5
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
        # --- v4 addition: AI pace-forecast positions --------
        pace_by_number, pace_label = _pace_positions(
            pace_races.get(nk_id))
        for key, pace in pace_by_number.items():
            horse = horses.setdefault(key, {
                col: None for col in SPEED_COLUMNS} | {"nk_recent": None})
            horse["pace"] = pace
        # --- v6 additions: netkeiba judgements / odds -------
        # Carried verbatim (numbers only) when a collection
        # supplies them; no current collection does, so on
        # today's files every horse takes the uniform nulls
        # below and the adapter's armed terms stay inert. The
        # odds side reads the normalised map (either collected
        # shape — see _normalise_odds_races).
        judged = (judgement_races.get(nk_id) or {}).get("horses") or {}
        odds_horses = odds_races.get(nk_id) or {}
        for key, horse in horses.items():
            entry_j = judged.get(key)
            if isinstance(entry_j, dict):
                horse["nkFormDev"] = _num(entry_j.get("nkFormDev"))
                horse["nkAiScore"] = _num(entry_j.get("nkAiScore"))
            entry_o = odds_horses.get(key)
            if isinstance(entry_o, dict):
                cells = {c: entry_o.get(c) for c in ODDS_CELLS}
                if entry_o.get("forecastWin") is not None:
                    cells["forecastWin"] = entry_o["forecastWin"]
                horse["odds"] = (cells if any(
                    v is not None for v in cells.values()) else None)
            # The newspaper marks join on (race, horse number)
            # alone — they never needed the race-details input.
            # Until v6 they were assigned only inside the
            # details runners loop above, so a build without
            # details (the 2026-11-18 collection run) silently
            # dropped every collected mark (press coverage 0
            # despite 279 marked horses on file). Assign here
            # for every horse the details loop did not reach.
            if horse.get("press") is None:
                entry_p = press_horses.get(key)
                horse["press"] = (entry_p
                                  if isinstance(entry_p, dict)
                                  else None)
        # --- 2026-11-19: each horse's data-analysis judgements
        # Join on (race, horse number) like the pace positions:
        # the judgements never needed the race-details input.
        analysis_horses = (analysis_races.get(nk_id)
                           or {}).get("horses") or {}
        if isinstance(analysis_horses, dict):
            for key, entry_a in analysis_horses.items():
                block = _horse_analysis_block(entry_a)
                if block is None:
                    continue
                horse = horses.setdefault(str(key), {
                    col: None for col in SPEED_COLUMNS}
                    | {"nk_recent": None})
                horse["horseAnalysis"] = block
        # --- 2026-11-19: course-persons sire rows as the
        # sireCourse fallback. The full sire table's record
        # (already inside pedigree, from _pedigree) wins; a
        # persons row fills only a horse whose sireCourse is
        # still missing. A horse with no profile at all gains a
        # minimal pedigree block carrying the row's sire name
        # and record (the rest stays null — not collected).
        for key, horse in horses.items():
            record = persons_sires.get((nk_id, key))
            if record is None:
                continue
            pedigree = horse.get("pedigree")
            if isinstance(pedigree, dict):
                if pedigree.get("sireCourse") is not None:
                    continue
                pedigree = dict(pedigree)
                pedigree["sireCourse"] = record["sireCourse"]
                horse["pedigree"] = pedigree
            else:
                horse["pedigree"] = {
                    "sire": record["sire"], "dam": None,
                    "damSire": None,
                    "sireCourse": record["sireCourse"],
                    "siblings": None}
        # --- 2026-11-19: course persons — this race's jockey /
        # trainer and their records at today's course, carried
        # verbatim for the adapter's course-persons trial terms.
        # A horse with no collected row for a kind simply lacks
        # that kind (not collected, never estimated).
        for key, horse in horses.items():
            block: dict = {}
            jockey = persons_jockeys.get((nk_id, key))
            if jockey is not None:
                block["jockey"] = jockey
            trainer = persons_trainers.get((nk_id, key))
            if trainer is not None:
                block["trainer"] = trainer
            if block:
                horse["coursePersons"] = block
        # Every horse carries every v2 field; a horse the detail
        # input did not cover (or a race with no detail input at
        # all) gets uniform nulls — not collected, never zero.
        for horse in horses.values():
            for field in V2_HORSE_FIELDS \
                    + ("pace", "horseAnalysis", "coursePersons") \
                    + V6_HORSE_FIELDS:
                horse.setdefault(field, None)
        if not horses and course is None:
            continue
        races[aq_id] = {"netkeibaRaceId": nk_id, "horses": horses,
                        "courseAnalysis": course,
                        "paceLabel": pace_label}
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
    coverage["pace"] = sum(1 for h in all_horses
                           if h.get("pace") is not None)
    # v6: the judgements / odds fields (0 until a collection
    # supplies them) and the derived-speed coverage, summed
    # race by race (the overlap feature is a race-level
    # computation, so it cannot be counted horse by horse).
    coverage["nkFormDev"] = sum(1 for h in all_horses
                                if h.get("nkFormDev") is not None)
    coverage["nkAiScore"] = sum(1 for h in all_horses
                                if h.get("nkAiScore") is not None)
    coverage["oddsDrift"] = sum(
        1 for h in all_horses if isinstance(h.get("odds"), dict)
        and h["odds"].get("publishWin") is not None
        and h["odds"].get("finalWin") is not None)
    coverage["oddsWpGap"] = sum(
        1 for h in all_horses if isinstance(h.get("odds"), dict)
        and h["odds"].get("finalWin") is not None
        and h["odds"].get("placeLow") is not None
        and h["odds"].get("placeHigh") is not None)
    # 2026-11-19 additions: the forecast-odds lines (carried
    # under their own name; they light no odds-movement term)
    # and the per-horse data-analysis judgements.
    coverage["oddsForecast"] = sum(
        1 for h in all_horses if isinstance(h.get("odds"), dict)
        and h["odds"].get("forecastWin") is not None)
    coverage["horseAnalysis"] = sum(
        1 for h in all_horses if h.get("horseAnalysis") is not None)
    # 2026-11-19 additions: the course persons (this race's
    # jockey / trainer records at today's course).
    coverage["courseJockey"] = sum(
        1 for h in all_horses
        if isinstance(h.get("coursePersons"), dict)
        and h["coursePersons"].get("jockey") is not None)
    coverage["courseTrainer"] = sum(
        1 for h in all_horses
        if isinstance(h.get("coursePersons"), dict)
        and h["coursePersons"].get("trainer") is not None)
    for race in races.values():
        for key, count in _derived_coverage(
                list(race["horses"].values())).items():
            coverage[key] = coverage.get(key, 0) + count
    # Zero detection (2026-11-19, the user's standing
    # instruction: collected material must ALL reach the
    # forecast): every expected field whose count is 0 is named
    # in the output itself, so a missing material is an
    # on-the-record "uncollected", never a silent zero.
    zero_coverage = [field for field, count in coverage.items()
                     if field != "horses" and count == 0]
    return {
        "version": "nk-materials-v10",
        "date": date,
        "source": "netkeiba-forward-collection",
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "fieldCoverage": coverage,
        "zeroCoverage": zero_coverage,
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
    parser.add_argument("--pace-forecast")
    parser.add_argument("--nk-judgements")
    parser.add_argument("--odds")
    parser.add_argument("--horse-analysis")
    parser.add_argument("--course-persons")
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
                    newspaper=_load(args.newspaper),
                    pace_forecast=_load(args.pace_forecast),
                    nk_judgements=_load(args.nk_judgements),
                    odds=_load(args.odds),
                    horse_analysis=_load(args.horse_analysis),
                    course_persons=_load(args.course_persons))
    out = (Path(args.out) if args.out else
           ROOT / "rewrite" / "data" / "nk_materials" / f"{args.date}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    coverage = payload["fieldCoverage"]
    print(f"wrote {out}: {len(payload['races'])} races, "
          f"{coverage['horses']} horses, coverage={coverage}")
    if payload["zeroCoverage"]:
        print("ZERO COVERAGE (expected fields with no data — "
              "uncollected, never silently zero): "
              + ", ".join(payload["zeroCoverage"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
