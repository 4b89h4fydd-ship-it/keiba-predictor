#!/usr/bin/env python3
"""Seal today's (or a date's) forecasts pre-off into the seal store.

Usage:
  python scripts/arvexq_rewrite_seal.py <ingest_db> <seal_db>

For every race in the ingest DB this builds the exact display payload
(the serve configuration: prior weights, beta 2.0), wraps it with the
prediction-time odds and source provenance, and seals it. Races whose
source detail already carries a confirmed result, and races whose
scheduled start has passed at seal time, are skipped and reported —
a forecast is never sealed after the fact.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite.analysis.forecast import forecast_race  # noqa: E402
from rewrite.analysis.pace import forecast_pace  # noqa: E402
from rewrite.analysis.tickets import generate_tickets  # noqa: E402
from rewrite.data.store import Store  # noqa: E402
from rewrite.output.api_shape import MODEL_VERSION, race_payload  # noqa: E402
from rewrite.output.sealing import SealCollisionError, SealStore  # noqa: E402

BETA = 2.0  # matches the serve configuration in arvexq_rewrite_serve.py
MODEL_KEY = f"{MODEL_VERSION}:beta{BETA}:prior-weights"
JST = ZoneInfo("Asia/Tokyo")


def scheduled_start(detail: dict, date: str) -> datetime | None:
    raw = detail.get("startTime") or detail.get("scheduledStartTime")
    if not raw or not isinstance(raw, str):
        return None
    try:
        hh, mm = raw.strip().split(":")[:2]
        local = datetime.combine(
            datetime.fromisoformat(date).date(), time(int(hh), int(mm)), tzinfo=JST
        )
    except (ValueError, TypeError):
        return None
    return local.astimezone(timezone.utc)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ingest = Store(sys.argv[1])
    seals = SealStore(sys.argv[2])
    now = datetime.now(timezone.utc)
    summary = {"sealed": [], "already_sealed": [], "skipped": []}
    try:
        details = {}
        for key, body, fetched_at, sha in ingest.db.execute(
            "SELECT race_key, body, fetched_at, sha256 FROM raw_snapshots "
            "WHERE kind='api_race_detail'"
        ):
            payload = json.loads(body)
            details[key] = {
                "detail": payload.get("detail") or {},
                "fetched_at": fetched_at, "sha256": sha,
            }
        for race in ingest.load_races():
            info = details.get(race.race_id)
            if info is None:
                summary["skipped"].append({"race": race.race_id, "reason": "no-source-detail"})
                continue
            detail = info["detail"]
            if (detail.get("result") or {}).get("status") == "確定":
                summary["skipped"].append({"race": race.race_id, "reason": "already-finished"})
                continue
            start = scheduled_start(detail, race.date)
            if start is not None and now >= start:
                summary["skipped"].append({"race": race.race_id, "reason": "after-scheduled-start"})
                continue
            # Build exactly what the serve path builds (same calls).
            forecast = forecast_race(race, beta=BETA)
            pace = forecast_pace(race)
            win_odds = {
                r.number: r.win_odds.value
                for r in race.runners
                if r.win_odds.present and isinstance(r.win_odds.value, (int, float))
            }
            tickets = generate_tickets(forecast, win_odds, calibration_validated=False)
            payload = {
                "kind": "arvexq-sealed-forecast",
                "racePayload": race_payload(
                    race, forecast, pace, tickets,
                    provenance={
                        "snapshot_sha256": info["sha256"],
                        "captured_at": info["fetched_at"],
                    },
                ),
                "predictionContext": {
                    "modelKey": MODEL_KEY,
                    "segment": race.segment.value,
                    "oddsAtPrediction": {
                        str(r.number): r.win_odds.value
                        for r in race.runners
                        if r.win_odds.present and isinstance(r.win_odds.value, (int, float))
                    },
                    "oddsSource": "production-api-detail",
                    "sourceFetchedAt": info["fetched_at"],
                    "sourceSnapshotSha256": info["sha256"],
                },
            }
            try:
                receipt = seals.seal(race.race_id, MODEL_KEY, payload,
                                     scheduled_start=start, now=now)
            except SealCollisionError as exc:
                summary["skipped"].append({"race": race.race_id, "reason": f"collision: {exc}"})
                continue
            bucket = "sealed" if receipt.sealed_at == now.isoformat() else "already_sealed"
            summary[bucket].append({
                "race": race.race_id, "sha256": receipt.payload_sha256,
                "pre_off": receipt.pre_off,
            })
    finally:
        ingest.close()
        seals.close()
    print(json.dumps({
        "model_key": MODEL_KEY, "sealed_at": now.isoformat(),
        "sealed": len(summary["sealed"]), "already_sealed": len(summary["already_sealed"]),
        "skipped": summary["skipped"],
        "sealed_races": summary["sealed"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
