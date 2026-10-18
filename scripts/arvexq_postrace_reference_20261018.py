"""Read-only, explicitly POST-RACE reference for the 2026-10-18 racecard.

Reuses the ALREADY installed observed-history baseline verbatim (no new
handicapping weights or bet selection). Archived current-race results, future
runs and archived predicted marks/bets are never inputs. Generated references
are NEVER pre-off predictions, betting advice, or historical backtest hits.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from arvexq.forecast.engine import build_prediction, VERSION as MODEL_VERSION
from arvexq.forecast.marks import generate_marks
from arvexq.forecast.inputs import prediction_input

VERSION = "arvexq-postrace-reference-20261018-v1"
DAY = "2026-10-18"
JST = ZoneInfo("Asia/Tokyo")


def _day(value):
    raw = str(value or "").strip()
    if len(raw) == 8 and raw.isascii() and raw.isdigit():
        raw = raw[:4] + "-" + raw[4:6] + "-" + raw[6:]
    try:
        return date.fromisoformat(raw.replace("/", "-")[:10])
    except ValueError:
        return None


def _archived_detail(path: Path, entry):
    wrapped = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(wrapped, dict) or wrapped.get("version") != "arvexq-full-payload-v1":
        raise ValueError("Unknown snapshot envelope")
    raw = gzip.decompress(base64.b64decode(wrapped["gzipBase64"], validate=True))
    if (hashlib.sha256(raw).hexdigest() != wrapped.get("sha256")
            or hashlib.sha256(raw).hexdigest() != entry.get("sha256")
            or len(raw) != wrapped.get("bytes")
            or len(raw) != entry.get("bytes")):
        raise ValueError("Snapshot content integrity mismatch")
    return json.loads(raw)


def _asof_input(detail, scheduled_day):
    facts = prediction_input(detail)
    excluded = 0
    # Never include current result, odds, stored marks/bets or unverified
    # undated career runs as of the race. DTO itself excludes result/odds.
    for horse in facts.get("horses", []):
        for key in ("recentRaces", "allPastRuns"):
            seen = horse.get(key)
            if not isinstance(seen, list):
                continue
            keep = []
            for run in seen:
                if not isinstance(run, dict):
                    continue
                when = _day(run.get("date") or run.get("raceDate") or run.get("race_date"))
                if when is None or when >= scheduled_day:
                    excluded += 1
                    continue
                keep.append(dict(run))
            horse[key] = keep
    return facts, excluded


def produce(static_root: Path, out_dir: Path, date_str=DAY):
    if date_str != DAY:
        raise ValueError("This static reference is restricted to the requested 2026-10-18 date")
    index_path = static_root / "saved-snapshots" / (date_str + ".json")
    if not index_path.is_file():
        return None
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("date") != date_str or not isinstance(index.get("races"), dict):
        raise ValueError("Bad archive index")
    entry_map = index["races"]
    records = {}
    for race_id, ref in sorted(entry_map.items()):
        record = {"raceId": race_id, "status": "insufficient_history",
                  "marks": [], "recommendedBets": [],
                  "recommendationStatus": "no_verified_preoff_ticket",
                  "retrospective": True, "countTowardsAccuracy": False}
        try:
            source = _archived_detail(static_root / "saved-snapshots" / ref["file"], ref)
            if (not isinstance(source, dict)
                    or source.get("id") != race_id or source.get("date") != date_str
                    or len(source.get("horses") or []) != ref.get("horses")):
                raise ValueError("Race identity / runner count differs from archive")
            inputs, excluded = _asof_input(source, date.fromisoformat(date_str))
            # Caller-supplied clock is the last instant before post. The
            # installed forecast formula is unchanged.
            start = datetime.fromisoformat(date_str + "T" + str(source["startTime"])[:5]).replace(tzinfo=JST)
            forecast = build_prediction(inputs, now=start - timedelta(seconds=1))
            record["excludedUndatedOrFutureRuns"] = excluded
            record["runnerNumbers"] = [
                int(h["horseNumber"]) for h in (source.get("horses") or [])
                if str(h.get("horseNumber") or "").isdigit()
            ]
            if forecast:
                rows = generate_marks(forecast)
                if rows:
                    record["status"] = "reference"
                    record["marks"] = [{"horseNumber": x["horseNumber"], "mark": x["mark"]} for x in rows]
                    record["modelVersion"] = MODEL_VERSION
        except (ValueError, KeyError, TypeError, OSError, EOFError, gzip.BadGzipFile):
            record["status"] = "unusable_archive"
        records[race_id] = record
    ready = sum(x["status"] == "reference" for x in records.values())
    payload = {"version": VERSION, "date": DAY, "mode": "POSTRACE_REFERENCE_NOT_PREOFF",
               "source": "stored race archive with post-race results excluded",
               "forecastModelVersion": MODEL_VERSION,
               "isHistoricPrediction": False, "canCountAsHit": False,
               "raceCount": len(records), "referenceCount": ready,
               "notAvailableCount": len(records) - ready, "races": records}
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (DAY + ".json")
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("POSTRACE_REFERENCE", DAY, "races", len(records), "references", ready,
          "insufficient", len(records) - ready)
    return payload


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[1] / "arvexq" / "ui" / "static"
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "dist" / "postrace-reference"
    produce(root, output)
