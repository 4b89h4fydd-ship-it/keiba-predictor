#!/usr/bin/env python3
"""Build / refresh ``rewrite/data/pace_scenario_history.jsonl``.

The standing history behind the published pace-scenario
frequencies: one JSON line per *finished* race, labelled under
``pace-label-v2`` by
``rewrite.analysis.pace_scenario_freq.realized_pace_label`` (the
early leaders' time-based deceleration against the frozen par
table ``rewrite/data/pace_label_par.json``).

Two extraction routes, both from real finished races only —
never from a forecast:

- ``result`` rows: a pack's own race, when the pack carries a
  final (確定) result.
- ``past-run`` rows: historical races reconstructed by grouping
  the pack horses' past-run records (``recentRaces`` /
  ``allPastRuns``) by raceId. The grouping accumulates across
  *all* input packs before labelling — one pack alone usually
  holds only a few of a historical race's runners. A ``result``
  row always wins over a ``past-run`` row for the same race.

A race that cannot be labelled (too few observed early leaders,
or no par for its surface) gets no line at all — excluded, never
guessed. Rows are stamped with ``labelVersion``; when refreshing,
rows stamped with a different version are dropped (the definition
changed — they are rebuilt from the packs given, never blended).

Usage:

    python3 scripts/build_pace_scenario_history.py PACK...

Each argument is a static race-pack JSON file
(``arvexq/ui/static/api-static/race/*.json``), a directory of
them, or an official snapshot file (a document with ``results``
entries wrapping race packs). The seed shipped on 2026-11-26 was
built this way from the official snapshot packs of 2026-11-18..25
(result races plus past-run reconstructions). Obihiro (ban-ei)
packs are excluded, as everywhere in ARVEXQ.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rewrite.analysis.pace_scenario_freq import (  # noqa: E402
    LABEL_VERSION, load_par_table, realized_pace_label)

HISTORY_PATH = ROOT / "rewrite" / "data" / "pace_scenario_history.jsonl"
PAR_PATH = ROOT / "rewrite" / "data" / "pace_label_par.json"

BAN_EI_TRACK = "帯広"


def iter_pack_details(path: Path):
    """Yield ``(detail, summary)`` for every race pack in a file."""
    if path.is_dir():
        for child in sorted(path.rglob("*.json")):
            yield from iter_pack_details(child)
        return
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(doc, dict):
        return
    if isinstance(doc.get("detail"), dict):
        yield doc["detail"], doc.get("summary") or {}
        return
    for entry in doc.get("results") or []:
        envelope = entry.get("detail") or {}
        inner = envelope.get("detail") or envelope
        if isinstance(inner, dict) and inner:
            yield inner, envelope.get("summary") or inner.get(
                "summary") or {}


def _label_row(raw: dict, source: str, par: dict):
    race_id = raw.get("race_id")
    track = raw.get("track")
    if not race_id or not track or BAN_EI_TRACK in str(track):
        return None
    labelled = realized_pace_label(
        raw["finishers"], surface=raw.get("surface"),
        distance=raw.get("distance"), condition=raw.get("condition"),
        par=par)
    if labelled is None:
        return None
    return {
        "race_id": race_id,
        "date": raw.get("date"),
        "track": track,
        "surface": raw.get("surface"),
        "distance": raw.get("distance"),
        "label": labelled["label"],
        "labelVersion": LABEL_VERSION,
        "statistic": labelled["statistic"],
        "z": labelled["z"],
        "source": source,
    }


def collect(argv: list[str]):
    """Gather raw (unlabelled) race records from all inputs.

    Returns ``(result_races, past_run_races)``: dicts keyed by
    race_id of ``{race_id, date, track, surface, distance,
    condition, finishers}``.
    """
    result_races: dict[str, dict] = {}
    grouped: dict[str, dict] = {}
    meta: dict[str, dict] = {}
    for arg in argv:
        for detail, summary in iter_pack_details(Path(arg)):
            result = detail.get("result") or {}
            finishers = result.get("finishers") or []
            race_id = detail.get("id")
            if (result.get("status") == "確定" and finishers
                    and race_id and race_id not in result_races):
                result_races[race_id] = {
                    "race_id": race_id,
                    "date": summary.get("race_date")
                    or detail.get("date"),
                    "track": summary.get("track")
                    or detail.get("track"),
                    "surface": summary.get("surface")
                    or detail.get("surface"),
                    "distance": summary.get("distance")
                    or detail.get("distance"),
                    "condition": summary.get("condition")
                    or detail.get("condition"),
                    "finishers": finishers,
                }
            for horse in detail.get("horses") or []:
                runs = []
                for key in ("recentRaces", "allPastRuns"):
                    value = horse.get(key)
                    if isinstance(value, list):
                        runs.extend(value)
                for run in runs:
                    rid = run.get("raceId")
                    if not rid:
                        continue
                    slot = grouped.setdefault(rid, {})
                    horse_key = (horse.get("name"),
                                 run.get("horseNumber"))
                    if horse_key not in slot:
                        slot[horse_key] = run
                    meta.setdefault(rid, run)
    past_run_races: dict[str, dict] = {}
    for rid, slot in grouped.items():
        if rid in result_races:
            continue  # the result route owns this race
        m = meta[rid]
        past_run_races[rid] = {
            "race_id": rid,
            "date": m.get("date"),
            "track": m.get("track"),
            "surface": m.get("surface"),
            "distance": m.get("distance"),
            "condition": m.get("condition"),
            "finishers": list(slot.values()),
        }
    return result_races, past_run_races


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    par = load_par_table(PAR_PATH)
    if not par["entries"]:
        print(f"par table missing or empty: {PAR_PATH}")
        return 2
    rows: dict[str, dict] = {}
    if HISTORY_PATH.exists():
        for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            # Rows from another label definition are dropped, never
            # blended; they are rebuilt from packs when available.
            if (row.get("race_id")
                    and row.get("labelVersion") == LABEL_VERSION):
                rows[row["race_id"]] = row
    result_races, past_run_races = collect(argv)
    counts = defaultdict(int)
    for source, races in (("past-run", past_run_races),
                          ("result", result_races)):
        for raw in races.values():
            row = _label_row(raw, source, par)
            if row is None:
                counts[f"unlabelled-{source}"] += 1
                continue
            rows[row["race_id"]] = row
            counts[f"labelled-{source}"] += 1
    ordered = sorted(rows.values(),
                     key=lambda r: (r.get("date") or "",
                                    r.get("race_id") or ""))
    HISTORY_PATH.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ordered),
        encoding="utf-8")
    print(f"history rows: {len(ordered)} "
          f"({dict(counts)}) -> {HISTORY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
