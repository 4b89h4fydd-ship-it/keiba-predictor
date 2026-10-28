#!/usr/bin/env python3
"""Shadow-seal the yukochi-style LATE lane (S2) into its own store.

Usage:
  python scripts/arvexq_yukochi_late_seal.py <ingest_db> <shadow_db> \
      <phase0_summary_json>
  python scripts/arvexq_yukochi_late_seal.py <ingest_db> <shadow_db> \
      <phase0_summary_json> --dry-run
  python scripts/arvexq_yukochi_late_seal.py --from-audit <ingest_db> \
      <audit_db> <race_id>

What this lane is (plan: yukochi-imitation-20261028/plan.md):
the frozen v1 configuration (lane_config LANE_WEIGHTS, beta 2.0)
re-scored about 30 minutes before the off on the field as it
actually stands — scratches and jockey changes applied, the day's
going/weather taken from the API summary, body weight recorded —
and sealed into a SEPARATE append-only shadow store. The v1 seal
store, the v8 shadow store and production payloads are never read
or written here (the v1 store is not even opened).

Hard rules:
- Sealing is gated on the Phase 0 availability audit: while the
  audit summary's pre-registered gates are not all true, window
  mode reports "waiting-for-gate" and seals nothing.
- The window is T-35..T-25 minutes. A race whose T-25 deadline has
  passed is recorded as missed and is NEVER sealed late; a late
  seal counted as a T-30 forecast would be back-fitting.
- Only Nankan tracks (大井・川崎・船橋・浦和), NAR segment.
- --from-audit is an offline dry-run on a captured Phase 0 audit
  snapshot: it builds and prints the late forecast but seals
  nothing, so the lane can be exercised before the gate opens.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.lane_config import LANE_BETA, LANE_WEIGHTS  # noqa: E402
from rewrite.analysis.late_lane import (  # noqa: E402
    apply_late_inputs,
    gate_open,
    late_inputs_from_api_payload,
    late_inputs_from_snapshot,
)
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.data.sources import API_BASE, BROWSER_UA  # noqa: E402
from rewrite.data.store import Store  # noqa: E402
from rewrite.output.api_shape import race_payload  # noqa: E402
from rewrite.output.sealing import SealCollisionError, SealStore  # noqa: E402
from rewrite.safety.contracts import Segment  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "arvexq_rewrite_seal",
    Path(__file__).resolve().parent / "arvexq_rewrite_seal.py")
_seal_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_seal_mod)
scheduled_start = _seal_mod.scheduled_start

MODEL_KEY = "arvexq-shadow-yukochi-late:v1-lane-weights:beta2.0"
NANKAN = {"大井", "川崎", "船橋", "浦和"}
JST = ZoneInfo("Asia/Tokyo")
WINDOW_OPEN_MIN = 35.0   # start processing at T-35
WINDOW_CLOSE_MIN = 25.0  # never seal at or after T-25


def http_get_json(path: str, timeout: float = 25.0) -> dict:
    request = urllib.request.Request(
        f"{API_BASE}{path}", headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_late_payload(race, late, *, fetched_at: datetime,
                       gate: dict | None) -> tuple[dict, dict]:
    """Score the late-updated race with the frozen lane config."""
    late_race = apply_late_inputs(race, late)
    weights = LANE_WEIGHTS.get(late_race.segment.value, {})
    forecast = forecast_race(late_race, beta=LANE_BETA, weights=weights)
    pace = forecast_pace(late_race)
    win_odds = {
        r.number: r.win_odds.value
        for r in late_race.runners
        if r.win_odds.present and isinstance(r.win_odds.value, (int, float))
    }
    tickets = generate_tickets(forecast, win_odds, calibration_validated=False)
    active_numbers = [r.number for r in late_race.active_runners]
    payload = {
        "kind": "arvexq-shadow-late-forecast",
        "racePayload": race_payload(
            late_race, forecast, pace, tickets,
            provenance={"captured_at": fetched_at.isoformat()},
        ),
        "predictionContext": {
            "modelKey": MODEL_KEY,
            "lane": "yukochi-s2-late",
            "baseModel": "frozen-v1-lane-weights",
            "segment": late_race.segment.value,
            "lateFetchedAt": fetched_at.isoformat(),
            "lateCondition": late.condition,
            "lateWeather": late.weather,
            "bodyWeightCoverage": round(
                late.body_weight_coverage(active_numbers), 4),
            "bodyWeightChangeCoverage": round(
                (sum(1 for n in active_numbers
                     if n in late.body_weight_change)
                 / len(active_numbers)) if active_numbers else 0.0, 4),
            "scratchedLate": sorted(late.scratched),
            "oddsAtPrediction": {
                str(n): v for n, v in sorted(late.win_odds.items())},
            "oddsSource": "production-api-detail-t30",
            "phase0Gate": gate,
        },
    }
    marks = {
        r.number: r.mark for r in forecast.runners if r.mark
    }
    return payload, marks


def window_mode(ingest_path: Path, shadow_path: Path,
                summary_path: Path, *, dry_run: bool,
                now: datetime) -> dict:
    open_now, gate = gate_open(summary_path)
    if not open_now and not dry_run:
        return {"status": "waiting-for-gate", "gate": gate, "sealed": 0}
    ingest = Store(str(ingest_path))
    seals = None
    if dry_run:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".sqlite3", delete=False)
        tmp.close()
        seals = SealStore(tmp.name)
    else:
        seals = SealStore(str(shadow_path))
    summary = {"status": "ok", "gate": gate, "sealed": [],
               "already_sealed": [], "missed": [], "not_in_window": 0,
               "errors": []}
    try:
        details = {}
        for key, body, fetched_at, sha in ingest.db.execute(
            "SELECT race_key, body, fetched_at, sha256 FROM raw_snapshots "
            "WHERE kind='api_race_detail'"
        ):
            payload = json.loads(body)
            details[key] = {"detail": payload.get("detail") or {},
                            "fetched_at": fetched_at, "sha256": sha}
        for race in ingest.load_races():
            if race.segment is not Segment.NAR or race.track not in NANKAN:
                continue
            info = details.get(race.race_id)
            if info is None:
                continue
            if (info["detail"].get("result") or {}).get("status") == "確定":
                continue
            start = scheduled_start(info["detail"], race.date)
            if start is None:
                continue
            minutes = (start - now).total_seconds() / 60.0
            if minutes > WINDOW_OPEN_MIN:
                summary["not_in_window"] += 1
                continue
            if minutes <= WINDOW_CLOSE_MIN:
                # Past the deadline (or already off): missed, never
                # sealed late. Only count races still ahead of the
                # off by less than the close as missed for today.
                if minutes > -180:
                    summary["missed"].append(
                        {"race": race.race_id, "minutes": round(minutes, 1)})
                continue
            try:
                payload_api = http_get_json(
                    f"/api/race/{urllib.parse.quote(race.race_id, safe='')}")
            except Exception as exc:  # fetch failure is recorded, not hidden
                summary["errors"].append(
                    {"race": race.race_id, "error": str(exc)[:200]})
                continue
            fetched_at = datetime.now(timezone.utc)
            if fetched_at >= start - timedelta(minutes=WINDOW_CLOSE_MIN):
                summary["missed"].append(
                    {"race": race.race_id, "minutes": round(minutes, 1),
                     "reason": "fetch-completed-after-close"})
                continue
            late = late_inputs_from_api_payload(payload_api)
            payload, marks = build_late_payload(
                race, late, fetched_at=fetched_at, gate=gate)
            try:
                receipt = seals.seal(race.race_id, MODEL_KEY, payload,
                                     scheduled_start=start, now=fetched_at)
            except SealCollisionError as exc:
                summary["errors"].append(
                    {"race": race.race_id, "error": f"collision: {exc}"})
                continue
            bucket = ("sealed" if receipt.sealed_at == fetched_at.isoformat()
                      else "already_sealed")
            summary[bucket].append({
                "race": race.race_id, "sha256": receipt.payload_sha256,
                "minutes_before": round(minutes, 1),
                "bw_coverage": payload["predictionContext"][
                    "bodyWeightCoverage"],
                "marks": {str(k): v for k, v in marks.items()},
            })
    finally:
        ingest.close()
        seals.close()
    summary["sealed"] = summary["sealed"]
    return summary


def from_audit_mode(ingest_path: Path, audit_db: Path,
                    race_id: str) -> dict:
    """Offline dry-run: rebuild one race's late forecast from a
    captured Phase 0 audit snapshot. Seals nothing."""
    import sqlite3
    db = sqlite3.connect(str(audit_db))
    row = db.execute(
        "SELECT snapshot_json, summary_condition, summary_weather, mode "
        "FROM audit_records WHERE race_id=? ORDER BY fetched_at DESC "
        "LIMIT 1", (race_id,)).fetchone()
    db.close()
    if row is None:
        return {"status": "no-audit-snapshot", "race": race_id}
    snapshot = json.loads(row[0])
    late = late_inputs_from_snapshot(
        snapshot, condition=row[1], weather=row[2])
    ingest = Store(str(ingest_path))
    try:
        race = next((r for r in ingest.load_races()
                     if r.race_id == race_id), None)
    finally:
        ingest.close()
    if race is None:
        return {"status": "race-not-in-ingest", "race": race_id}
    payload, marks = build_late_payload(
        race, late, fetched_at=datetime.now(timezone.utc), gate=None)
    ctx = payload["predictionContext"]
    base = forecast_race(
        race, beta=LANE_BETA,
        weights=LANE_WEIGHTS.get(race.segment.value, {}))
    base_marks = {r.number: r.mark for r in base.runners if r.mark}
    return {
        "status": "dry-run-ok",
        "race": race_id,
        "audit_mode": row[3],
        "late_condition": ctx["lateCondition"],
        "body_weight_coverage": ctx["bodyWeightCoverage"],
        "body_weight_change_coverage": ctx["bodyWeightChangeCoverage"],
        "scratched_late": ctx["scratchedLate"],
        "odds_at_prediction": ctx["oddsAtPrediction"],
        "marks_late": {str(k): v for k, v in marks.items()},
        "marks_base_frozen": {str(k): v for k, v in base_marks.items()},
        "marks_changed": marks != base_marks,
    }


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--from-audit":
        if len(args) != 4:
            print(__doc__)
            return 2
        result = from_audit_mode(Path(args[1]), Path(args[2]), args[3])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if len(args) < 3:
        print(__doc__)
        return 2
    dry_run = "--dry-run" in args
    now = datetime.now(timezone.utc)
    result = window_mode(Path(args[0]), Path(args[1]), Path(args[2]),
                         dry_run=dry_run, now=now)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
