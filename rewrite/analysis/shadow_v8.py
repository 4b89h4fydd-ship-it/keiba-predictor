"""Shadow lane for the v8 candidate model (margin-weighted Elo +
speed index v2), built for forward validation on unseen races.

The frozen v1 lane (rewrite/analysis/lane_config.py) is untouched by
this module. The v8 candidate fitted weights live here, copied
verbatim from goals/arvexq/hidden_files/fitted-weights-v8.json
(status: candidate-not-adopted-pending-forward-validation). Only the
two segments the candidate was fitted for (jra_flat, nar) exist;
races in other segments have no candidate and are skipped honestly.

Point-in-time discipline (the whole point of the shadow lane):

- Elo ratings are a pure function of an append-only event ledger.
  Features for a target date use only result events dated strictly
  before that date and first seen no later than that date. The full
  ratings snapshot used for a date is stored (append-only) with its
  hash, so the as-of state is reproducible byte-for-byte.
- Speed v2 residuals are recomputed deterministically from an
  append-only run ledger restricted to runs first seen by the target
  date; variant estimation uses only runs dated on or before the
  adjusted run's own date, exactly as in the v8 experiment.
- The exact extras fed into each sealed forecast are recorded inside
  the sealed payload, so a seal stays auditable even if the ledger
  later grows.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import exp
from pathlib import Path
from typing import Optional

from ..data.normalize import RaceRecord, RunnerRecord
from ..safety.contracts import Segment
from ..safety.probability import distribution, marginals
from .ability import LOWER_IS_BETTER, _minmax, extract_features
from .forecast import (
    FLOOR_FRACTION,
    PROBABILITY_STATUS,
    RaceForecast,
    RunnerForecast,
    _assign_marks,
    _pace_adjustments,
)
from .pace import forecast_pace

MODEL_KEY = "arvexq-shadow-v8-elo-speed2-natkey1"
MODEL_VERSION = "arvexq-shadow-v8-candidate"
FEATURE_SET_VERSION = "v8-elo-speed2-forward-2-natkey"

ELO_K = 24.0
ELO_INIT = 1500.0
SPEED_DECAY = 0.85

# spd2 residuals are seconds-like deficits: lower is faster = better.
# (The v8 research scripts added these to LOWER_IS_BETTER at runtime;
# the shadow lane keeps the extension local so the frozen modules are
# not mutated.)
LOWER_IS_BETTER_V8 = LOWER_IS_BETTER | {"spd2_recent", "spd2_best"}

# Verbatim from fitted-weights-v8.json (combined Elo + spd2 candidate,
# refitted on 2026-10-03..23). speed_rel/speed_best are replaced by
# spd2_recent/spd2_best and intentionally absent.
WEIGHTS: dict[str, dict[str, float]] = {
    "jra_flat": {
        "form": 0.00515625, "speed": 0.4, "distance": 0.4,
        "track": 0.009375, "surface": 0.2, "condition": 0.00625,
        "jockey": 0.1, "closing": 0.005, "consistency": 0.005,
        "top3_rate": 0.005, "rest": 0.005625, "weight_shift": 0.005,
        "class_recent": 0.005, "class_drop": 0.005,
        "elo": 0.2, "elo_rel": 0.1, "elo_evidence": 0.005,
        "spd2_recent": 0.4, "spd2_best": 0.4,
    },
    "nar": {
        "form": 0.03, "speed": 0.05, "distance": 0.05, "track": 0.32,
        "surface": 0.05, "condition": 0.075, "jockey": 0.075,
        "closing": 0.005, "consistency": 0.025, "top3_rate": 0.32,
        "rest": 0.005, "weight_shift": 0.005, "class_recent": 0.06,
        "class_drop": 0.0075,
        "elo": 0.025, "elo_rel": 0.025, "elo_evidence": 0.005,
        "spd2_recent": 0.4, "spd2_best": 0.4,
    },
}
BETAS: dict[str, float] = {"jra_flat": 4.0, "nar": 3.0}

EXTRA_FEATURES = ("elo", "elo_rel", "elo_evidence",
                  "spd2_recent", "spd2_best")


def horse_key_of(runner: RunnerRecord,
                 race_date: Optional[str] = None) -> Optional[str]:
    """Stable cross-day identity for the shadow ledgers.

    The payload's per-entry ``id`` is NOT a horse registry code.
    Measured over the 2026-10-02..28 ingest DBs (15,701 runner
    appearances), it changed on essentially every appearance: of
    4,117 horses (name+sex, age-consistent) that ran on >= 2 distinct
    days, only 6 kept a single id, and the id sets of the same horse
    were disjoint between the backtest and pre-off ingests (0/427
    overlap). Keying the ledgers by it would fragment every horse's
    history by appearance and orphan every finisher event, so the
    cross-day accumulation the ledgers exist for could never happen.

    The ledgers therefore key on the natural identity
    ``name|sex|birth_year``. Birth year is derived as race year minus
    age, which is exact under the Jan-1 aging rule; the components
    were present on 100% (name) / 99.9% (sex, age) of measured
    appearances, versus 77.3% for the payload id. With this key,
    80.3% of the 2026-10-28 runners already had an earlier-October
    appearance to accumulate from. ``race_date`` should always be
    passed; without it the birth-year component is left empty.
    """
    if not (runner.name.present and runner.name.value):
        return None
    sex = ""
    if runner.sex.present and runner.sex.value:
        sex = str(runner.sex.value)
    birth_year = ""
    age = runner.age.value if runner.age.present else None
    if isinstance(age, (int, float)) and not isinstance(age, bool) \
            and race_date:
        try:
            birth_year = str(int(str(race_date)[:4]) - int(age))
        except (TypeError, ValueError):
            birth_year = ""
    return f"name:{runner.name.value}|{sex}|{birth_year}"


def _num(value):
    """Normalize an Obs number for identity keys: 1600 and 1600.0 are
    the same distance (the v8 experiment's tuple keys equate them)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def race_key_of(date, track, title, distance) -> str:
    return json.dumps(
        [date, track, title, _num(distance)],
        ensure_ascii=False, separators=(",", ":"),
    )


def run_key_of(horse_key, date, track, surface, distance, time_seconds) -> str:
    return json.dumps(
        [horse_key, date, track, surface, _num(distance),
         float(time_seconds)],
        ensure_ascii=False, separators=(",", ":"),
    )


def _canonical(payload) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


class StateDriftError(ValueError):
    """A stored snapshot disagrees with a recomputation. The stored
    snapshot stays authoritative; drift is surfaced, never repaired
    silently."""


class ShadowStateStore:
    """Append-only ledgers + snapshots for the shadow lane, kept in
    the same SQLite file as the shadow seals (separate tables from
    sealed_forecasts, which rewrite.output.sealing manages)."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS shadow_elo_events(
              race_key TEXT NOT NULL,
              race_ref TEXT NOT NULL DEFAULT '',
              event_date TEXT NOT NULL,
              horse_key TEXT NOT NULL,
              finish INTEGER NOT NULL,
              time_seconds REAL,
              source TEXT NOT NULL,
              first_seen_date TEXT NOT NULL,
              recorded_at TEXT NOT NULL,
              PRIMARY KEY(race_key, race_ref, horse_key, source)
            );
            CREATE TRIGGER IF NOT EXISTS shadow_elo_events_no_update
              BEFORE UPDATE ON shadow_elo_events
              BEGIN SELECT RAISE(ABORT,'shadow ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS shadow_elo_events_no_delete
              BEFORE DELETE ON shadow_elo_events
              BEGIN SELECT RAISE(ABORT,'shadow ledger is append-only'); END;
            CREATE TABLE IF NOT EXISTS shadow_speed_runs(
              run_key TEXT PRIMARY KEY,
              horse_key TEXT NOT NULL,
              run_date TEXT NOT NULL,
              track TEXT,
              surface TEXT,
              distance REAL,
              time_seconds REAL NOT NULL,
              first_seen_date TEXT NOT NULL,
              recorded_at TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS shadow_speed_runs_no_update
              BEFORE UPDATE ON shadow_speed_runs
              BEGIN SELECT RAISE(ABORT,'shadow ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS shadow_speed_runs_no_delete
              BEFORE DELETE ON shadow_speed_runs
              BEGIN SELECT RAISE(ABORT,'shadow ledger is append-only'); END;
            CREATE TABLE IF NOT EXISTS shadow_snapshots(
              as_of_date TEXT NOT NULL,
              kind TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(as_of_date, kind)
            );
            CREATE TRIGGER IF NOT EXISTS shadow_snapshots_no_update
              BEFORE UPDATE ON shadow_snapshots
              BEGIN SELECT RAISE(ABORT,'shadow snapshots are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS shadow_snapshots_no_delete
              BEFORE DELETE ON shadow_snapshots
              BEGIN SELECT RAISE(ABORT,'shadow snapshots are append-only'); END;
            """
        )

    def close(self) -> None:
        self.db.close()

    # -- ledgers ----------------------------------------------------
    def add_elo_events(self, rows: list[tuple]) -> int:
        before = self.db.total_changes
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO shadow_elo_events VALUES(?,?,?,?,?,?,?,?,?)",
                rows,
            )
        return self.db.total_changes - before

    def add_speed_runs(self, rows: list[tuple]) -> int:
        before = self.db.total_changes
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO shadow_speed_runs VALUES(?,?,?,?,?,?,?,?,?)",
                rows,
            )
        return self.db.total_changes - before

    def elo_events(self, before_date: str, seen_by: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT race_key, race_ref, event_date, horse_key, finish,"
            " time_seconds, source FROM shadow_elo_events"
            " WHERE event_date < ? AND first_seen_date <= ?",
            (before_date, seen_by),
        ).fetchall()
        return [
            {"race_key": r[0], "race_ref": r[1], "event_date": r[2],
             "horse_key": r[3], "finish": r[4], "time_seconds": r[5],
             "source": r[6]}
            for r in rows
        ]

    def speed_runs(self, seen_by: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT run_key, horse_key, run_date, track, surface,"
            " distance, time_seconds FROM shadow_speed_runs"
            " WHERE first_seen_date <= ?",
            (seen_by,),
        ).fetchall()
        return [
            {"run_key": r[0], "horse": r[1], "date": r[2], "track": r[3],
             "surface": r[4], "distance": r[5], "time": r[6]}
            for r in rows
        ]

    # -- snapshots --------------------------------------------------
    def put_snapshot(self, as_of_date: str, kind: str, payload: dict) -> str:
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        existing = self.db.execute(
            "SELECT payload_sha256 FROM shadow_snapshots"
            " WHERE as_of_date=? AND kind=?",
            (as_of_date, kind),
        ).fetchone()
        if existing:
            if existing[0] != digest:
                raise StateDriftError(
                    f"snapshot drift for {as_of_date}/{kind}: stored "
                    f"{existing[0][:12]}… vs recomputed {digest[:12]}…"
                )
            return digest
        with self.db:
            self.db.execute(
                "INSERT INTO shadow_snapshots VALUES(?,?,?,?,?)",
                (as_of_date, kind, _canonical(payload).decode("utf-8"),
                 digest, datetime.now(timezone.utc).isoformat()),
            )
        return digest

    def get_snapshot(self, as_of_date: str, kind: str) -> Optional[dict]:
        row = self.db.execute(
            "SELECT payload_json, payload_sha256 FROM shadow_snapshots"
            " WHERE as_of_date=? AND kind=?",
            (as_of_date, kind),
        ).fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        if hashlib.sha256(_canonical(payload)).hexdigest() != row[1]:
            raise StateDriftError(
                f"snapshot hash mismatch for {as_of_date}/{kind}")
        return payload


# --------------------------------------------------------------------
# Elo: pairwise margin-weighted updates, date-batch order.
# Semantics replicate fit-v8-features.build_elo, with the ledger's
# first_seen discipline added on top.
# --------------------------------------------------------------------

def _elo_apply(ratings: dict, starts: dict, field: list) -> None:
    ordered = sorted(field, key=lambda x: x[1])
    for key, _, _ in ordered:
        ratings.setdefault(key, ELO_INIT)
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            ka, _, ta = ordered[i]
            kb, _, tb = ordered[j]
            if isinstance(ta, (int, float)) and isinstance(tb, (int, float)):
                margin = max(0.0, float(tb) - float(ta))
                w = min(2.5, max(0.6, 0.6 + 1.2 * margin))
            else:
                w = 1.0
            ea = 1.0 / (1.0 + 10 ** (-(ratings[ka] - ratings[kb]) / 400.0))
            delta = ELO_K * w * (1.0 - ea)
            ratings[ka] += delta
            ratings[kb] -= delta
    for key in {k for k, _, _ in ordered}:
        starts[key] = starts.get(key, 0) + 1


def build_elo_state(events: list[dict]) -> tuple[dict, dict, int]:
    """Apply ledger events in date order; return (ratings, starts,
    fields_applied). Finisher fields (complete lists, grouped by race)
    suppress reconstructed partial fields under the same race key."""
    complete_keys = {e["race_key"] for e in events if e["source"] == "finisher"}
    fields_by_date: dict[str, list] = defaultdict(list)
    finisher_groups: dict[tuple, list] = defaultdict(list)
    for e in events:
        if e["source"] == "finisher":
            finisher_groups[(e["event_date"], e["race_ref"])].append(e)
    for (date, _ref), rows in finisher_groups.items():
        field = [(r["horse_key"], r["finish"], r["time_seconds"])
                 for r in rows if isinstance(r["finish"], int)]
        if len(field) >= 3:
            fields_by_date[date].append((rows[0]["race_key"], field))
    recon: dict[str, dict] = defaultdict(dict)
    for e in events:
        if e["source"] == "recon" and e["race_key"] not in complete_keys:
            recon[e["race_key"]][e["horse_key"]] = (
                e["event_date"], e["finish"], e["time_seconds"])
    for race_key, per_horse in recon.items():
        if len(per_horse) < 3:
            continue
        finishes = [f for _, f, _ in per_horse.values()]
        if max(Counter(finishes).values()) >= 3:
            continue  # ambiguous merge of two races under one key
        date = min(d for d, _, _ in per_horse.values())
        field = [(k, f, t) for k, (_, f, t) in per_horse.items()]
        fields_by_date[date].append((race_key, field))
    ratings: dict[str, float] = {}
    starts: dict[str, int] = defaultdict(int)
    applied = 0
    for date in sorted(fields_by_date):
        for _key, field in sorted(fields_by_date[date], key=lambda x: x[0]):
            _elo_apply(ratings, starts, field)
            applied += 1
    return ratings, dict(starts), applied


# --------------------------------------------------------------------
# Speed v2: variant-adjusted residuals. Semantics replicate
# fit-v8-features.build_speed2 over the ledger run set.
# --------------------------------------------------------------------

def build_speed_adjusted(runs: list[dict]) -> tuple[dict, dict]:
    """Return (adjusted, varn): run_key -> adjusted residual / variant
    support ratio. par and variants use only information dated on or
    before each run's own date."""
    by_date: dict[str, list] = defaultdict(list)
    for run in runs:
        by_date[run["date"]].append(run)
    par_pool: dict[tuple, list[float]] = defaultdict(list)
    horse_resids: dict[str, list[float]] = defaultdict(list)
    adjusted: dict[str, float] = {}
    varn: dict[str, float] = {}
    for date in sorted(by_date):
        day = by_date[date]
        pars = {c: statistics.median(v)
                for c, v in par_pool.items() if len(v) >= 5}
        raw: dict[str, float] = {}
        for run in day:
            cond = (run["track"], run["surface"], run["distance"])
            if cond in pars:
                raw[run["run_key"]] = run["time"] - pars[cond]
        groups: dict[tuple, list[float]] = defaultdict(list)
        for run in day:
            if run["run_key"] not in raw:
                continue
            prior = horse_resids.get(run["horse"])
            if prior:
                groups[(run["track"], run["surface"])].append(
                    raw[run["run_key"]] - statistics.median(prior))
        variants = {g: statistics.median(v)
                    for g, v in groups.items() if len(v) >= 5}
        var_counts = {g: len(v) for g, v in groups.items() if len(v) >= 5}
        for run in day:
            par_pool[(run["track"], run["surface"],
                      run["distance"])].append(run["time"])
            if run["run_key"] not in raw:
                continue
            g = (run["track"], run["surface"])
            if g in variants:
                adjusted[run["run_key"]] = raw[run["run_key"]] - variants[g]
                varn[run["run_key"]] = min(1.0, var_counts[g] / 20.0)
            horse_resids[run["horse"]].append(raw[run["run_key"]])
    return adjusted, varn


def race_extras(
    race: RaceRecord,
    ratings: dict, starts: dict,
    adjusted: dict,
) -> dict[int, dict[str, float]]:
    """v8 extras for one race from as-of state. Mirrors the feature
    sections of fit-v8-features.build_elo / build_speed2."""
    per: dict[int, dict[str, float]] = {}
    field_ratings = {}
    for r in race.active_runners:
        key = horse_key_of(r, race.date)
        if key and starts.get(key, 0) >= 1:
            field_ratings[r.number] = ratings[key]
    mean_r = (sum(field_ratings.values()) / len(field_ratings)
              if field_ratings else None)
    for r in race.active_runners:
        key = horse_key_of(r, race.date)
        n = starts.get(key, 0) if key else 0
        entry: dict[str, float] = {"elo_evidence": min(n, 12) / 12.0}
        if key and n >= 1 and mean_r is not None:
            entry["elo"] = ratings[key]
            entry["elo_rel"] = ratings[key] - mean_r
        if key:
            adj = []
            for idx, run in enumerate(r.past_runs):
                t = run.time_seconds.value
                if not isinstance(t, (int, float)) or t <= 0:
                    continue
                rk = run_key_of(key, run.date, run.track.value,
                                run.surface.value, run.distance.value,
                                float(t))
                if rk in adjusted:
                    adj.append((adjusted[rk], SPEED_DECAY ** idx))
            if adj:
                total_w = sum(w for _, w in adj)
                entry["spd2_recent"] = (
                    sum(v * w for v, w in adj) / total_w)
                entry["spd2_best"] = min(v for v, _ in adj[:5])
        per[r.number] = entry
    return per


def forecast_race_v8(
    race: RaceRecord,
    extras: Optional[dict[int, dict[str, float]]] = None,
) -> RaceForecast:
    """Score one race with the v8 candidate: harness-identical
    combination of base features + merged extras under the fitted
    weights and per-segment beta, then the production pace/probability
    /marks path. Raises KeyError for segments without a candidate."""
    segment = race.segment.value
    weights = WEIGHTS[segment]
    beta = BETAS[segment]
    active = list(race.active_runners)
    feats = {}
    for r in active:
        feat = extract_features(race, r)
        feats[r.number] = feat
    for number, extra in (extras or {}).items():
        if number not in feats:
            continue
        for key in EXTRA_FEATURES:
            value = extra.get(key)
            if value is not None:
                feats[number].raw[key] = value
                feats[number].evidence_counts[key] = 1
    normalized: dict[str, dict[int, float]] = {}
    for feature in weights:
        present = {
            n: feats[n].raw[feature]
            for n in feats if feats[n].raw.get(feature) is not None
        }
        normalized[feature] = _minmax(present, feature in LOWER_IS_BETTER_V8)
    pace = forecast_pace(race)
    adjustments = _pace_adjustments(race, pace)
    scores: dict[int, float] = {}
    for number, feat in feats.items():
        if race.segment is Segment.DEBUT or feat.evidence_runs == 0:
            continue
        available = {
            k: normalized[k][number]
            for k in weights if number in normalized.get(k, {})
        }
        if len(available) < 3:
            continue
        total_w = sum(weights[k] for k in available)
        scores[number] = round(
            sum(available[k] * weights[k] for k in available) / total_w, 4)
    names = {r.number: (r.name.value if r.name.present else None)
             for r in active}
    if len(scores) < 3:
        runners = tuple(
            RunnerForecast(
                number=n, name=names[n], ability_score=scores.get(n),
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="insufficient-scored-runners",
            )
            for n in sorted(feats)
        )
        return RaceForecast(race.race_id, beta, PROBABILITY_STATUS,
                            runners, "insufficient-scored-runners")
    mean_score = sum(scores.values()) / len(scores)
    strengths: dict[int, float] = {}
    for n, s in scores.items():
        factor, _ = adjustments.get(n, (1.0, ()))
        strengths[n] = exp(beta * (s - mean_score)) * factor
    floor = FLOOR_FRACTION * min(strengths.values())
    floored = set()
    for number in feats:
        if number not in strengths:
            strengths[number] = floor
            floored.add(number)
    probs = marginals(distribution(strengths))
    ranked = sorted(probs, key=lambda n: (-probs[n][0], -probs[n][2], n))
    marks = _assign_marks(ranked, probs)
    runners = []
    for number in sorted(feats):
        if number in probs:
            factor, reasons = adjustments.get(number, (1.0, ()))
            runners.append(RunnerForecast(
                number=number, name=names[number],
                ability_score=scores.get(number),
                strength=round(strengths[number], 6),
                pace_adjustment=factor, pace_reasons=reasons,
                p_win=round(probs[number][0], 4),
                p_top2=round(probs[number][1], 4),
                p_top3=round(probs[number][2], 4),
                mark=marks.get(number, ""),
                status=("unscored-floor-strength" if number in floored
                        else "forecast-uncalibrated"),
            ))
        else:
            runners.append(RunnerForecast(
                number=number, name=names[number],
                ability_score=scores.get(number),
                strength=None, pace_adjustment=1.0, pace_reasons=(),
                p_win=None, p_top2=None, p_top3=None, mark="",
                status="insufficient-evidence",
            ))
    return RaceForecast(race.race_id, beta, PROBABILITY_STATUS,
                        tuple(runners), "ok")
