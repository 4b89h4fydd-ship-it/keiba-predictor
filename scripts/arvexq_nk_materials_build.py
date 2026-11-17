#!/usr/bin/env python3
"""Build one date's production nk-materials file from the forward
collection outputs.

The publish lane (scripts/arvexq_rewrite_publish.py) reads
``rewrite/data/nk_materials/<date>.json`` — the transport that
carries the collected netkeiba materials into GitHub Actions,
in the same style as the v8 extras. This builder is the
normaliser between the collection side and that file; the
collection crons' saved outputs are its inputs:

  --speed-index       speed-index.json from the forward
                      collection (per netkeiba race_id, per horse:
                      nk_best / nk_avg5 / nk_dist / nk_course /
                      nk_recent — the speed page's full columns)
  --course-analysis   course-analysis.json (per netkeiba race_id:
                      the course-analysis tables as collected)
  --targets           course-analysis-targets.json (the netkeiba
                      race_id <-> ARVEXQ race_id mapping)

Output format (version "nk-materials-v2"):

  {"version": "nk-materials-v2", "date": ..., "source": ...,
   "generatedAt": ...,
   "races": {<arvexq_race_id>: {
       "netkeibaRaceId": <netkeiba race_id>,
       "horses": {<horse number as str>: {
           "nk_best": int|null, "nk_avg5": int|null,
           "nk_dist": int|null, "nk_course": int|null,
           "nk_recent": [int|null, ...] | null}},
       "courseAnalysis": {<the collected course-analysis entry,
                           minus its arvexq_race_id echo>} | null}}}

  The v2 label marks the adjustment definition that consumes
  the file (the course-analysis tables now feed the weighted
  course terms for NAR; see rewrite/analysis/nk_materials.py).
  The fields themselves are unchanged from v1, and the publish
  lane's parser does not gate on the version string.

Rules: values are carried verbatim from the collection (nulls
stay null — a "-" / 未 cell is missing material, never imputed);
a race present in the targets but missing from a collection file
keeps the other file's data with the missing side null/empty; a
race in NO collection file is omitted. Nothing is estimated.

Usage:
  python3 scripts/arvexq_nk_materials_build.py --date 2026-11-17 \
      --speed-index <path> --course-analysis <path> \
      --targets <path> [--out rewrite/data/nk_materials/2026-11-17.json]
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


def build(date: str, speed_index: dict, course_analysis: dict,
          targets: dict) -> dict:
    speed_races = (speed_index.get("races")
                   if isinstance(speed_index, dict) else None) or {}
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
        if not horses and course is None:
            continue
        races[aq_id] = {"netkeibaRaceId": nk_id, "horses": horses,
                        "courseAnalysis": course}
    return {
        "version": "nk-materials-v2",
        "date": date,
        "source": "netkeiba-forward-collection",
        "generatedAt": datetime.now(JST).isoformat(timespec="seconds"),
        "races": races,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--speed-index", required=True)
    parser.add_argument("--course-analysis", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()

    def _load(path):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    payload = build(args.date, _load(args.speed_index),
                    _load(args.course_analysis), _load(args.targets))
    out = (Path(args.out) if args.out else
           ROOT / "rewrite" / "data" / "nk_materials" / f"{args.date}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    covered = sum(1 for r in payload["races"].values()
                  if any(h.get("nk_avg5") is not None
                         for h in r["horses"].values()))
    print(f"wrote {out}: {len(payload['races'])} races, "
          f"{covered} with speed-index coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
