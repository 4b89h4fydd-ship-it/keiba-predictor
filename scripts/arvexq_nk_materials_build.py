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
                      "nkFormDev" / "nkAiScore" fields. The
                      nkFormDev half is produced by
                      scripts/arvexq_nk_page_collect.py
                      --barometer (the JRA 調子偏差値 page;
                      2026-11-21 fix2). nkAiScore remains
                      unproduced: its source (the AI総合スコア
                      page) is gated behind netkeiba's Master
                      course, outside the current plan.
  --stable-comments   (optional, 2026-11-21 fix2) per-horse stable
                      comments (厩舎コメント), the shape
                      scripts/arvexq_nk_page_collect.py writes:
                      {"races": {<netkeiba race_id>: {"horses":
                      {<number>: {"comment": text}},
                      "published": bool}}}. A race with
                      "published": false has no comments in the
                      source (掲載は新馬戦・特別レースのみ) — the
                      correct state, recorded as no comment, never
                      as a failure. The builder joins them by
                      (race, horse number) into each horse's
                      "comment_text" (the integrated evaluation's
                      comment input) and carries the text verbatim
                      as "stableComment". A newspaper short comment
                      (短評) saved in the press entry fills
                      comment_text only where no stable comment
                      exists. The press entry's 調教評価 letter is
                      also extracted into "grade" (the integrated
                      evaluation's grade input, until now never
                      populated by any build) and a saved press
                      "rating" into "pressRating".
  --odds              (optional, v6) per-horse odds snapshots.
                      May be given more than once (2026-11-21
                      fix2): the files are successive snapshots
                      in argument order, and _normalise_odds_
                      snapshots merges them — the FIRST actual
                      win line becomes publishWin and the LAST
                      becomes finalWin, so the odds-drift term
                      finally has its two points (前夜保存→朝に
                      比較). A single snapshot behaves exactly as
                      before (finalWin only). Provenance is kept:
                      forecast lines never become actual cells.
                      Two collected shapes are accepted (see
                      _normalise_odds_races): the dict shape
                      {"races": {<netkeiba race_id>: {"horses":
                      {<number>: {"publishWin": ..., "finalWin":
                      ..., "placeLow": ..., "placeHigh": ...}}}}
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
  --race-entries      (optional, 2026-11-23) per-horse race
                      entries in the shape {"races": {<netkeiba
                      race_id>: {"horses": {<number>: {"name":
                      ..., "jockey": ..., "trainer": ...}}}}}
                      — the entered horses' jockey / trainer
                      names as collected from the race's entry
                      (shutuba) page. Together with the course-
                      analysis persons FULL tables （得意な騎手 /
                      得意な調教師 carried in --course-analysis)
                      it supplies each horse's coursePersons
                      record by a name join, for the days the
                      per-horse course-persons rows were not
                      collected. A name that does not appear in
                      the course's table has no record there —
                      the horse simply carries no row, never an
                      estimated one. Race-details runners carry
                      the same names and are used the same way
                      when no entries file covers the race.
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

Output format (version "nk-materials-v12"):

  {"version": "nk-materials-v12", "date": ..., "source": ...,
   "generatedAt": ...,
   "fieldCoverage": {<per-field horse counts over the file>},
   "zeroCoverage": [<names of the expected fields whose count
                    is 0 — the uncollected list, on the record
                    in the file itself and in the build log, so
                    a zero can never pass silently>],
   "zeroCoverageExplained": {<field: reason for the zeros whose
                    absence is positively established from the
                    build inputs — see _classify_zero_coverage>},
   "zeroCoverageUnexplained": [<zero fields with no established
                    reason: missing material. main() exits
                    non-zero when this is non-empty>],
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
import re
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


def _person_table_index(course_entry, table_key) -> dict:
    """{person name: {"name", "starts", "wins", "top3",
    "winRate"}} from one course-analysis persons FULL table
    （得意な騎手 / 得意な調教師） of today's course. The rows
    carry the same column layout as the sire table (name,
    1st, 2nd, 3rd, others, starts, ...) that _sire_course
    reads. A row whose counts cannot be read is dropped,
    never repaired."""
    out: dict = {}
    if not isinstance(course_entry, dict):
        return out
    table = course_entry.get(table_key)
    if not isinstance(table, dict):
        return out
    for row in table.get("行") or []:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        name = row[0]
        if not isinstance(name, str) or not name:
            continue
        first = _int_cell(row[1])
        second = _int_cell(row[2])
        third = _int_cell(row[3])
        starts = _int_cell(row[5])
        if first is None or starts is None or starts <= 0:
            continue
        out[name] = {"name": name, "starts": starts,
                     "wins": first,
                     "top3": first + (second or 0) + (third or 0),
                     "winRate": round(first / starts, 4)}
    return out


def _person_name(value, strip_affiliation: bool = False):
    """A person's name from an entry / runner cell, or None.
    Trainer cells on the race record carry the affiliation as
    a leading token ("栗東 加藤公", "美浦 上原佑", NAR yards
    the same way); the course tables key on the bare name, so
    for trainers the LAST whitespace-separated token is the
    name. Anything else passes through stripped — an unmatched
    name simply finds no table row, never a guessed one."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if strip_affiliation:
        parts = text.split()
        if len(parts) > 1:
            text = parts[-1]
    return text or None


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
    field is carried as-is.

    Two collected shapes are accepted (2026-11-23): the build
    shape (positions keyed start / corner3 / corner4, each a
    list of groups, label under "pace") and the collection's
    raw shape (positions keyed start / c3 / c4, each a FLAT
    list of horse numbers in forecast order — every horse its
    own group — label under "pace_ai"). The collection cron
    names the raw file in its builder invocation, so accepting
    only the build shape silently zeroed the pace coverage
    whenever the conversion step was skipped; the conversion
    is a reshape of the same diagram, never an estimate."""
    if not isinstance(pace_entry, dict):
        return {}, None
    positions = pace_entry.get("positions")
    if not isinstance(positions, dict):
        return {}, None
    label = pace_entry.get("pace")
    if not isinstance(label, str):
        label = pace_entry.get("pace_ai")
    phase_keys = {"start": "start", "corner3": "corner3",
                  "corner4": "corner4", "c3": "corner3",
                  "c4": "corner4"}
    out: dict = {}
    for raw_key, phase in phase_keys.items():
        groups = positions.get(raw_key)
        if not isinstance(groups, list):
            continue
        flat: list = []
        for group in groups:
            if isinstance(group, int) and not isinstance(group, bool):
                flat.append(group)  # raw shape: flat order list
                continue
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


def _normalise_odds_snapshots(odds) -> dict:
    """{netkeiba race_id: {number: odds cells}} from one odds
    payload (the legacy behaviour of _normalise_odds_races) or a
    LIST of payloads read as successive snapshots in order
    (2026-11-21 fix2, audit B4: the odds-drift term needs TWO
    actual-odds points and no collection ever wrote publishWin).

    Merge rule per horse, over the snapshots in order:
      - every snapshot's actual win line (a list-shape "actual"
        race's win_odds, or a dict shape's finalWin cell) is one
        observation; the LAST observation becomes finalWin and,
        when at least two observations exist, the FIRST becomes
        publishWin — the evening save compared against the
        morning save, exactly the two-stage snapshot the audit
        prescribed;
      - a dict shape's explicit publishWin cell is a sealed
        publish-time value and always wins over the derived one;
      - placeLow / placeHigh come from the last snapshot that
        carried them;
      - forecastWin is carried from the last snapshot that had
        one and is never promoted to an actual cell.
    A single snapshot therefore behaves exactly as the legacy
    normaliser did (finalWin only, no publishWin)."""
    if not isinstance(odds, list):
        return _normalise_odds_races(odds)
    merged: dict = {}
    for payload in odds:
        snap = _normalise_odds_races(payload)
        for nk_id, horses in snap.items():
            target = merged.setdefault(str(nk_id), {})
            for number, cells in horses.items():
                cur = target.setdefault(str(number), {})
                observations = cur.setdefault("_actualWins", [])
                if cells.get("finalWin") is not None:
                    observations.append(cells["finalWin"])
                if cells.get("publishWin") is not None \
                        and cur.get("publishWin") is None:
                    cur["publishWin"] = cells["publishWin"]
                for cell in ("placeLow", "placeHigh", "forecastWin"):
                    if cells.get(cell) is not None:
                        cur[cell] = cells[cell]
    for horses in merged.values():
        for cur in horses.values():
            observations = cur.pop("_actualWins", [])
            if observations:
                cur["finalWin"] = observations[-1]
                if cur.get("publishWin") is None \
                        and len(observations) >= 2:
                    cur["publishWin"] = observations[0]
    return merged


# ------------------------------------------------------------------
# Press comment / grade extraction (2026-11-21 fix2, audit B6/B7)
# ------------------------------------------------------------------

_CHOKYO_GRADE_RE = re.compile(r"([ABCD])\s*$")
_PRESS_COMMENT_KEYS = ("tanpyo", "short_comment", "comment")


def _press_grade(press) -> str | None:
    """The training-evaluation grade letter from a newspaper
    entry: an explicit "grade" the collection saved, else the
    trailing letter of the 調教評価 text ("好気配B" -> "B") the
    newspaper collection has always carried inside "chokyo".
    The letter set is the page's own (A-D); the integrated
    evaluation scores A/B/C and treats anything else as
    unscored — the builder carries the letter verbatim either
    way, never a mapped substitute."""
    if not isinstance(press, dict):
        return None
    grade = press.get("grade")
    if isinstance(grade, str) and grade.strip() in ("A", "B", "C", "D"):
        return grade.strip()
    chokyo = press.get("chokyo")
    if isinstance(chokyo, str):
        m = _CHOKYO_GRADE_RE.search(chokyo.strip())
        if m:
            return m.group(1)
    return None


def _press_comment(press) -> str | None:
    """The newspaper short comment (短評) from a press entry,
    under whichever key a collection saved it. None when the
    entry carries none (today's collections save none — the
    short comment lives in the premium newspaper view — so this
    lights up the moment a collection adds the key)."""
    if not isinstance(press, dict):
        return None
    for key in _PRESS_COMMENT_KEYS:
        text = press.get(key)
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _press_rating(press):
    """The newspaper rating (レーティング) from a press entry,
    numeric only, else None. Carried as the horse's pressRating;
    no integrated-evaluation term reads it yet — it is recorded
    in the materials file (and counted in fieldCoverage) so the
    collected value is on record, not silently dropped."""
    if not isinstance(press, dict):
        return None
    return _num(press.get("rating"))


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

# ------------------------------------------------------------------
# Zero-coverage classification (2026-11-25, collection-circuit
# audit S4).  A zero is "explained" only when the reason is
# positively established from the build's own inputs — never
# assumed.  Everything else stays unexplained, and main() exits
# non-zero on any unexplained zero, so a whole missing material
# (2026-11-24: bestTime / headToHead / horseAnalysis / grade all 0
# and placed anyway) stops the placing procedure on a
# machine-readable signal instead of an agent reading stdout.
# ------------------------------------------------------------------

def _classify_zero_coverage(zero_fields, *, jra_present,
                            odds_snapshots, stable_unpublished_only):
    explained: dict = {}
    unexplained: list = []
    for field in zero_fields:
        reason = None
        if field == "nkAiScore":
            # The AI総合スコア page is gated behind netkeiba's
            # Master course, outside the current plan; the field
            # is never produced (see the --nk-judgements note).
            reason = ("master-course-only source, outside the "
                      "current plan; never produced")
        elif field == "pressRating" and not jra_present:
            # The newspaper rating column exists only in JRA
            # papers; an all-NAR day has no rating to collect.
            reason = ("no JRA races in this build: NAR newspapers "
                      "carry no rating column")
        elif field in ("oddsDrift", "oddsWpGap", "oddsForecast") \
                and odds_snapshots == 0:
            reason = "no odds snapshot supplied to this build"
        elif field == "oddsDrift" and odds_snapshots == 1:
            reason = ("single odds snapshot: drift needs a first "
                      "and a last point")
        elif field == "stableComment" and stable_unpublished_only:
            reason = ("the source published no stable comments "
                      "for these races (published=false)")
        if reason:
            explained[field] = reason
        else:
            unexplained.append(field)
    return explained, unexplained


def build(date: str, speed_index: dict, course_analysis: dict,
          targets: dict, race_details: dict | None = None,
          horse_profiles: dict | None = None,
          newspaper: dict | None = None,
          pace_forecast: dict | None = None,
          nk_judgements: dict | None = None,
          odds: dict | list | None = None,
          horse_analysis: dict | None = None,
          course_persons: dict | None = None,
          stable_comments: dict | None = None,
          race_entries: dict | None = None) -> dict:
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
    stable_races = (stable_comments.get("races")
                    if isinstance(stable_comments, dict)
                    else None) or {}
    odds_races = _normalise_odds_snapshots(odds)
    analysis_races = (horse_analysis.get("races")
                      if isinstance(horse_analysis, dict)
                      else None) or {}
    persons_sires = _persons_sire_index(course_persons)
    persons_jockeys = _persons_kind_index(
        course_persons, course_analysis, "jockeys")
    persons_trainers = _persons_kind_index(
        course_persons, course_analysis, "trainers")
    entries_races = (race_entries.get("races")
                     if isinstance(race_entries, dict)
                     else None) or {}
    races: dict = {}
    for target in targets.get("targets") or []:
        nk_id = str(target.get("netkeiba_race_id") or "")
        aq_id = str(target.get("arvexq_race_id") or "")
        if not nk_id or not aq_id:
            continue
        speed_entry = speed_races.get(nk_id) or {}
        raw_horses = speed_entry.get("horses") or {}
        horses: dict = {}
        # The entered horses' names, by number — the roster the
        # details-independent joins below stand on (the speed
        # page and the newspaper both carry the name per number;
        # the speed entry wins, the press entry fills).
        names: dict = {}
        for key, values in raw_horses.items():
            if not isinstance(values, dict):
                continue
            horse = {col: values.get(col) for col in SPEED_COLUMNS}
            if isinstance(values.get("name"), str) \
                    and values["name"].strip():
                names[str(key)] = values["name"].strip()
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
        # The entered horses' jockey / trainer names, by number
        # — from the race-entries collection when it covers the
        # race, else from the race-details runners. These names
        # drive the course-persons full-table join below.
        persons_by_number: dict = {}
        entries_horses = (entries_races.get(nk_id)
                          or {}).get("horses") or {}
        if isinstance(entries_horses, dict):
            for key, entry_e in entries_horses.items():
                if not isinstance(entry_e, dict):
                    continue
                persons_by_number[str(key)] = {
                    "jockey": _person_name(entry_e.get("jockey")),
                    "trainer": _person_name(
                        entry_e.get("trainer"),
                        strip_affiliation=True),
                }
        for number, runner, _runs in runners:
            cell = persons_by_number.setdefault(
                str(number), {"jockey": None, "trainer": None})
            if cell["jockey"] is None:
                cell["jockey"] = _person_name(runner.get("jockey"))
            if cell["trainer"] is None:
                cell["trainer"] = _person_name(
                    runner.get("trainer"), strip_affiliation=True)
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
            # --- 2026-11-21 fix2 (B6/B7): the comment / grade
            # inputs the integrated evaluation has always read
            # (comment_text at weight 0.25, grade at 0.20) but no
            # build ever populated — the adapter read them from
            # the horse block and the builder never wrote them,
            # so both terms were structurally dark on every race.
            press = horse.get("press")
            if isinstance(press, dict):
                grade = _press_grade(press)
                if grade is not None:
                    horse["grade"] = grade
                rating = _press_rating(press)
                if rating is not None:
                    horse["pressRating"] = rating
                short = _press_comment(press)
                if short is not None:
                    horse["comment_text"] = short
            stable = (stable_races.get(nk_id)
                      or {}).get("horses") or {}
            entry_s = stable.get(key) \
                if isinstance(stable, dict) else None
            if isinstance(entry_s, dict):
                text = entry_s.get("comment")
                if isinstance(text, str) and text.strip():
                    horse["stableComment"] = text.strip()
                    # The stable's own words are the comment
                    # input's primary source; a newspaper short
                    # comment only fills a horse without one.
                    horse["comment_text"] = text.strip()
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
        # --- 2026-11-23: the details-independent pedigree join.
        # Until now the pedigree block was assigned ONLY inside
        # the race-details runners loop above, so a build with
        # no details input (2026-11-23: the API was down, no
        # details directory existed) produced pedigree = 0 and
        # sireCourse = 0 even though the date's horse profiles
        # (690 horses, sire / dam / siblings complete) and the
        # course-analysis sire table were both on file. The
        # roster does not need the details: the speed page and
        # the newspaper carry every entered horse's name by
        # number. Join profiles by that name, exactly as the
        # details loop did by the runner's name. This pass runs
        # after the pace loop has seeded every entered horse
        # into the roster (the maiden races have no speed
        # entries), and before the sire-row fallback below, so
        # the full table's record still wins.
        for key, horse in horses.items():
            if horse.get("pedigree") is not None:
                continue
            name = names.get(key)
            if name is None:
                press = press_horses.get(key)
                if isinstance(press, dict) \
                        and isinstance(press.get("name"), str) \
                        and press["name"].strip():
                    name = press["name"].strip()
            if name is None:
                continue
            pedigree = _pedigree(profiles.get(name), course)
            if pedigree is not None:
                horse["pedigree"] = pedigree
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
        # --- 2026-11-23: the course-persons full-table join.
        # The collected per-horse rows (above) win; a kind they
        # do not cover is filled from the course-analysis FULL
        # table （得意な騎手 / 得意な調教師） by the entered
        # horse's own jockey / trainer name. Until now the
        # builder carried only the per-horse rows, so a day
        # whose rows were not collected (2026-11-23: rows all
        # empty) produced courseJockey / courseTrainer = 0
        # even though the full tables were on file for every
        # course. The join is a reshape of the table's real
        # rows — a person absent from the table has no record
        # at this course and the horse carries none.
        jockey_table = _person_table_index(course, "得意な騎手")
        trainer_table = _person_table_index(course, "得意な調教師")
        for key, horse in horses.items():
            block: dict = {}
            jockey = persons_jockeys.get((nk_id, key))
            if jockey is not None:
                block["jockey"] = jockey
            trainer = persons_trainers.get((nk_id, key))
            if trainer is not None:
                block["trainer"] = trainer
            entry_names = persons_by_number.get(key) or {}
            if "jockey" not in block \
                    and entry_names.get("jockey") is not None:
                record = jockey_table.get(entry_names["jockey"])
                if record is not None:
                    block["jockey"] = record
            if "trainer" not in block \
                    and entry_names.get("trainer") is not None:
                record = trainer_table.get(entry_names["trainer"])
                if record is not None:
                    block["trainer"] = record
            if block:
                horse["coursePersons"] = block
        # Every horse carries every v2 field; a horse the detail
        # input did not cover (or a race with no detail input at
        # all) gets uniform nulls — not collected, never zero.
        for horse in horses.values():
            for field in V2_HORSE_FIELDS \
                    + ("pace", "horseAnalysis", "coursePersons") \
                    + V6_HORSE_FIELDS \
                    + ("grade", "comment_text", "stableComment",
                       "pressRating"):
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
    # 2026-11-23: the siblings block joins the counted fields —
    # it is carried inside pedigree and (from nk-materials-v14)
    # read by the adapter's siblings term, so its coverage is
    # on the record like every other expected field.
    coverage["siblings"] = sum(
        1 for h in all_horses
        if isinstance(h.get("pedigree"), dict)
        and isinstance(h["pedigree"].get("siblings"), dict))
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
    # 2026-11-21 fix2 (B6/B7): the comment / grade wiring. grade
    # and commentText count what actually reached the integrated
    # evaluation's inputs; stableComment and pressRating count
    # the verbatim records.
    coverage["grade"] = sum(1 for h in all_horses if h.get("grade"))
    coverage["commentText"] = sum(
        1 for h in all_horses if h.get("comment_text"))
    coverage["stableComment"] = sum(
        1 for h in all_horses if h.get("stableComment"))
    coverage["pressRating"] = sum(
        1 for h in all_horses if h.get("pressRating") is not None)
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
    explained, unexplained = _classify_zero_coverage(
        zero_coverage,
        jra_present=any(str(rid).startswith("jra-") for rid in races)
        or any((d or {}).get("circuit") == "中央"
               for d in (race_details or {}).values()),
        odds_snapshots=(len(odds) if isinstance(odds, list)
                        else 1 if odds else 0),
        stable_unpublished_only=bool(stable_races) and all(
            isinstance(e, dict) and e.get("published") is False
            for e in stable_races.values()))
    return {
        "version": "nk-materials-v12",
        "date": date,
        "source": "netkeiba-forward-collection",
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "fieldCoverage": coverage,
        "zeroCoverage": zero_coverage,
        "zeroCoverageExplained": explained,
        "zeroCoverageUnexplained": unexplained,
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
    parser.add_argument("--odds", action="append")
    parser.add_argument("--horse-analysis")
    parser.add_argument("--course-persons")
    parser.add_argument("--race-entries")
    parser.add_argument("--stable-comments")
    parser.add_argument("--out")
    args = parser.parse_args()

    def _load(path):
        if not path:
            return {}
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    # 2026-11-21 fix2: an input a collection saved into the same
    # forward directory is picked up even when the caller did not
    # name it — a saved material must not sit unused because an
    # argument was never added (the judgements and horse-analysis
    # files spent days in exactly that state). An explicit
    # argument always wins over discovery.
    base_dir = None
    for candidate in (args.newspaper, args.speed_index,
                      args.pace_forecast):
        if candidate:
            base_dir = Path(candidate).parent
            break

    def _discover(name, given):
        if given or base_dir is None:
            return given
        sibling = base_dir / name
        return str(sibling) if sibling.exists() else given

    args.nk_judgements = _discover("nk-judgements.json",
                                   args.nk_judgements)
    args.horse_analysis = _discover("horse-analysis.json",
                                    args.horse_analysis)
    args.stable_comments = _discover("stable-comments.json",
                                     args.stable_comments)
    args.race_entries = _discover("race-entries.json",
                                  args.race_entries)
    # Odds snapshots: every odds*.json sibling joins the named
    # ones, each file once, in file-mtime order (collection
    # order) — the two-stage snapshot merge then has its evening
    # and morning points without a caller change.
    odds_paths = list(args.odds or [])
    if base_dir is not None:
        known = {Path(p).resolve() for p in odds_paths}
        odds_paths += [str(p) for p in base_dir.glob("odds*.json")
                       if p.resolve() not in known]

    def _mtime(path):
        try:
            return Path(path).stat().st_mtime
        except OSError:
            return 0.0

    odds_paths.sort(key=_mtime)
    odds_payloads = [_load(p) for p in odds_paths]
    if len(odds_payloads) > 1:
        print("odds snapshots merged in order: "
              + ", ".join(Path(p).name for p in odds_paths))
    odds_arg = (odds_payloads if len(odds_payloads) != 1
                else odds_payloads[0] if odds_payloads else None)

    payload = build(args.date, _load(args.speed_index),
                    _load(args.course_analysis), _load(args.targets),
                    race_details=load_race_details(args.race_details_dir),
                    horse_profiles=_load(args.horse_profiles),
                    newspaper=_load(args.newspaper),
                    pace_forecast=_load(args.pace_forecast),
                    nk_judgements=_load(args.nk_judgements),
                    odds=odds_arg,
                    horse_analysis=_load(args.horse_analysis),
                    course_persons=_load(args.course_persons),
                    stable_comments=_load(args.stable_comments),
                    race_entries=_load(args.race_entries))
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
    explained = payload.get("zeroCoverageExplained") or {}
    if explained:
        print("ZERO COVERAGE EXPLAINED (known absences, on the "
              "record): " + "; ".join(
                  f"{field}: {reason}"
                  for field, reason in explained.items()))
    unexplained = payload.get("zeroCoverageUnexplained") or []
    if unexplained:
        # The file above stays on disk as the record, but the
        # build is NOT a success: the placing procedure must stop
        # here instead of shipping a material with whole fields
        # missing (collection-circuit audit S4).
        print("ZERO COVERAGE UNEXPLAINED (missing material with "
              "no registered reason — do not place this build): "
              + ", ".join(unexplained))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
