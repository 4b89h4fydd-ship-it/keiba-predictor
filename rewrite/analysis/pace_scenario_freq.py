"""Empirical pace-scenario frequencies from *realized* historical races.

Building block for measuring ``scenarioProbabilities`` instead of
leaving them null forever. Wired into the published payload on
2026-11-26 (user directive): the publisher reads a standing history
file (``rewrite/data/pace_scenario_history.jsonl``) and passes the
per-race frequency into ``master_v1`` and ``api_shape``, so
``scenarioFrequencyMeasured`` flips to True exactly for the races
whose profile has enough measured history, and stays False (with
``scenarioProbabilities`` null) everywhere else.

Realized label definition — ``pace-label-v2`` (2026-11-26, user
decision "fix the pace label first, then publish"):

The v1 label counted *positional* front runners in the finished
race (first-corner position / field size <= 0.35, >= 3 such runners
-> "fast"). That ratio is a mechanical function of field size: in
any field of 9+ runners at least 3 horses always satisfy it, and
195/195 measured fields of 9+ were labelled "fast". Its frequencies
also failed to beat the unconditional climatology in walk-forward
(Brier 0.0388 vs 0.0350). v1 is retired; see the label-v2 study
report for the full audit.

v2 labels a finished race by *time*, not positions:

- For each finisher that actually contested the early lead
  (first-corner position <= ``FRONT_MAX_POSITION``) and has both a
  finish time T and a last-3F time L, compute its deceleration
  ``b = (T - L) * 600 / (D - 600) - L`` seconds: the early part's
  per-600m pace minus the last-3F pace. Negative means the horse
  was dragged fast early and slowed late.
- The race statistic B is the median of b over those leaders
  (at least ``MIN_FRONT_OBSERVED`` required, else unlabelled).
- B is adjusted for track condition: on wet tracks (稍重/重/不良)
  the whole field decelerates more regardless of pace, so a frozen
  per-course condition shift (wet minus good median, estimated on
  the design period) is removed first.
- The adjusted B is standardized against a frozen par table
  (``rewrite/data/pace_label_par.json``: median / MAD spread per
  surface x distance, design period ending 2026-11-17):
  ``z = (B_adj - par_median) / par_spread``. Labels:
  z <= -0.45 -> "fast", z >= +0.45 -> "slow", else "normal".

By construction the label cannot be a function of field size (it
never reads the field size), and on the design + November data it
splits all field-size buckets across all three labels. Measured
validation (label-v2 study report, 2026-11-26): early leaders
reached the board at 0.495 (slow) / 0.396 (normal) / 0.349 (fast)
— the classic pace gradient — and the walk-forward frequency beat
climatology on both Brier (0.6252 vs 0.6649) and LogLoss (1.0327
vs 1.0960), n=109, coverage 100%. The forward-validation
registration (candidate C) is being re-registered as v2 on this
definition; its stage verdict remains the final arbiter.

Separation of concerns: labels are computed from *finished* races
only (learning side). The published frequency for a target race is
computed from history dated strictly before that race, and the
forecast side never reads a result. History rows are stamped with
``labelVersion``; the frequency counter refuses rows stamped with
a different version, so two definitions can never blend silently.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path
from typing import Iterable, Optional

LABEL_VERSION = "pace-label-v2"
SCENARIOS = ("slow", "normal", "fast")
# Minimum historical sample before a frequency is reported at all.
MIN_SAMPLE = 20

# --- pace-label-v2 constants (frozen; see module docstring) ---
FRONT_MAX_POSITION = 3
MIN_FRONT_OBSERVED = 2
THRESHOLD_Z = 0.45
MIN_PAR_RACES = 20
SPREAD_FLOOR_SECONDS = 0.5
WET_CONDITIONS = ("稍重", "重", "不良")
GOOD_CONDITION = "良"


def condition_group(condition) -> Optional[str]:
    """Map a recorded track condition to the adjustment group."""
    if condition == GOOD_CONDITION:
        return "good"
    if condition in WET_CONDITIONS:
        return "wet"
    return None


def _time_of(finisher: dict) -> Optional[float]:
    for key in ("timeSeconds", "time"):
        value = finisher.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _last3f_of(finisher: dict) -> Optional[float]:
    for key in ("last3FSeconds", "last3fSeconds", "last3f"):
        value = finisher.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _first_corner_of(finisher: dict) -> Optional[float]:
    for key in ("cornerPositions", "corners"):
        corners = finisher.get(key) or []
        if corners and isinstance(corners[0], (int, float)):
            return corners[0]
    return None


def front_deceleration(finishers: Iterable[dict],
                       distance) -> Optional[float]:
    """Median early-leader deceleration B (seconds), or None.

    Only finishers that contested the early lead (first-corner
    position <= FRONT_MAX_POSITION) and carry both a finish time
    and a last-3F time contribute. Fewer than MIN_FRONT_OBSERVED
    such leaders means the race's pace shape was not observed well
    enough to label — None, never a guess.
    """
    if not isinstance(distance, (int, float)) or distance <= 600:
        return None
    values = []
    for finisher in finishers:
        corner = _first_corner_of(finisher)
        if corner is None or corner > FRONT_MAX_POSITION:
            continue
        t = _time_of(finisher)
        last3f = _last3f_of(finisher)
        if t is None or last3f is None or t <= last3f:
            continue
        values.append(((t - last3f) * 600.0 / (distance - 600)) - last3f)
    if len(values) < MIN_FRONT_OBSERVED:
        return None
    return st.median(values)


def load_par_table(path) -> dict:
    """Load the frozen pace-label-v2 par table (JSON).

    Returns ``{"entries": {(surface, distance): (median, spread)},
    "shift_keys": {(surface, distance): shift},
    "shift_surfaces": {surface: shift}}``. A missing or unreadable
    file yields empty tables, which makes every label None
    (unmeasured) rather than guessed.
    """
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"entries": {}, "shift_keys": {}, "shift_surfaces": {}}
    entries = {}
    for key, value in (doc.get("par") or {}).items():
        surface, _, dist = key.rpartition("|")
        try:
            entries[(surface, int(dist))] = (
                float(value["median"]), float(value["spread"]))
        except (KeyError, TypeError, ValueError):
            continue
    shifts = doc.get("conditionShifts") or {}
    shift_keys = {}
    for key, value in (shifts.get("keys") or {}).items():
        surface, _, dist = key.rpartition("|")
        try:
            shift_keys[(surface, int(dist))] = float(value)
        except (TypeError, ValueError):
            continue
    shift_surfaces = {}
    for surface, value in (shifts.get("surfaces") or {}).items():
        try:
            shift_surfaces[surface] = float(value)
        except (TypeError, ValueError):
            continue
    return {"entries": entries, "shift_keys": shift_keys,
            "shift_surfaces": shift_surfaces}


def _condition_shift(par: dict, surface, distance) -> float:
    key = (surface, distance)
    if key in par["shift_keys"]:
        return par["shift_keys"][key]
    return par["shift_surfaces"].get(surface, 0.0)


def _par_for(par: dict, surface, distance):
    entries = par["entries"]
    if (surface, distance) in entries:
        return entries[(surface, distance)]
    candidates = [(abs(dist - distance), dist)
                  for (surf, dist) in entries if surf == surface]
    if candidates:
        _, nearest = min(candidates)
        return entries[(surface, nearest)]
    return None


def realized_pace_label(finishers: Iterable[dict], *, surface,
                        distance, condition,
                        par: dict) -> Optional[dict]:
    """Label one finished race under pace-label-v2.

    ``finishers`` are the race's finisher records (dicts with
    corner positions, finish time, last-3F time — both pack key
    spellings are accepted). ``par`` is a table from
    ``load_par_table``. Returns ``{"label", "statistic", "z"}``
    or None when the race was not observed well enough, or no par
    covers its surface — excluded, never guessed.
    """
    statistic = front_deceleration(finishers, distance)
    if statistic is None:
        return None
    adjusted = statistic
    if condition_group(condition) == "wet":
        adjusted -= _condition_shift(par, surface, distance)
    par_entry = _par_for(par, surface, distance)
    if par_entry is None:
        return None
    median, spread = par_entry
    if spread <= 0:
        return None
    z = (adjusted - median) / spread
    if z <= -THRESHOLD_Z:
        label = "fast"
    elif z >= THRESHOLD_Z:
        label = "slow"
    else:
        label = "normal"
    return {"label": label, "statistic": round(statistic, 4),
            "z": round(z, 4)}


def scenario_frequencies(history: Iterable[dict], *, track: str,
                         surface: str, distance,
                         min_sample: int = MIN_SAMPLE) -> Optional[dict]:
    """Empirical slow/normal/fast frequencies for one race profile.

    ``history`` items are realized-label records:
    ``{"track": ..., "surface": ..., "distance": ..., "label": ...}``
    (label None items are ignored, as are rows stamped with a
    different ``labelVersion``). Scopes widen from exact
    track+surface+distance, to track+surface, to surface only; the
    first scope reaching ``min_sample`` wins. Returns None when no
    scope has enough measured history — the frequency is then
    genuinely unmeasured and callers must keep null.
    """
    records = [h for h in history
               if h.get("label") in SCENARIOS
               and h.get("labelVersion", LABEL_VERSION) == LABEL_VERSION]
    scopes = (
        ("track-surface-distance",
         lambda h: h.get("track") == track and h.get("surface") == surface
         and h.get("distance") == distance),
        ("track-surface",
         lambda h: h.get("track") == track and h.get("surface") == surface),
        ("surface",
         lambda h: h.get("surface") == surface),
    )
    for scope_name, match in scopes:
        subset = [h for h in records if match(h)]
        if len(subset) < min_sample:
            continue
        counts = {name: 0 for name in SCENARIOS}
        for h in subset:
            counts[h["label"]] += 1
        total = len(subset)
        return {
            "slow": round(counts["slow"] / total, 4),
            "normal": round(counts["normal"] / total, 4),
            "fast": round(counts["fast"] / total, 4),
            "sample": total,
            "scope": scope_name,
            "labelVersion": LABEL_VERSION,
        }
    return None


def load_scenario_history(path) -> list[dict]:
    """Read a standing realized-label history file (JSON Lines).

    Each line is one finished race's record (``race_id``, ``date``,
    ``track``, ``surface``, ``distance``, ``label`` ...), exactly the
    shape ``scenario_frequencies`` consumes. A missing or unreadable
    file means no measured history: an empty list is returned and
    every caller publishes unmeasured (null) rather than failing.
    Malformed lines are skipped, never repaired by guessing.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            records.append(row)
    return records


def scenario_frequency_for(history: Iterable[dict], *, track: str,
                           surface: str, distance,
                           before_date: Optional[str] = None,
                           min_sample: int = MIN_SAMPLE) -> Optional[dict]:
    """Frequency for one race, using only history from before it.

    ``before_date`` (the target race's own date, ISO format) keeps
    the measurement walk-forward: rows dated on or after the race
    are excluded, so a standing history file that has already been
    extended past the race date can never leak the future into a
    published frequency. Rows without a usable date are kept only
    when ``before_date`` is None.
    """
    rows = list(history)
    if before_date:
        rows = [h for h in rows
                if isinstance(h.get("date"), str)
                and h["date"] < before_date]
    return scenario_frequencies(rows, track=track, surface=surface,
                                distance=distance, min_sample=min_sample)
