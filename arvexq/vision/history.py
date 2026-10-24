"""Internal race-video research store and temporally safe horse-history joins.

Input is an ARVEXQ video_detector report, not footage supplied to the PWA.
Historical race identity must be independently matched before any telemetry
can contribute to a later horse's feature vector. Derived observations are
not automatically assigned positive/negative ability points.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from typing import Any

VERSION = "arvexq-internal-vision-history-v1"


def _date(value: Any) -> str:
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except (ValueError, TypeError):
        return ""


def _measured(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        f = float(value)
    except (ValueError, TypeError):
        return None
    return f if isfinite(f) else None


def compact_video_evidence(report: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Save a research-only summary, excluding the original copyright video."""
    if (not isinstance(report, dict)
            or report.get("version") != "arvexq-video-detector-v1"
            or report.get("predictionApplied") is not False):
        raise ValueError("genuine unpromoted video analysis required")
    manifest, measured = report.get("manifest") or {}, report.get("measurements") or {}
    source = manifest.get("source") or {}
    if (source.get("rightsVerified") is not True or source.get("calibrationVerified") is not True
            or source.get("coordinateSystem") != "ground-plane-meters"
            or not measured.get("videoSha256")
            or measured.get("videoSha256") != source.get("sha256")
            or measured.get("analysisStatus") != "tracking-measurements-not-a-validated-video-model"):
        raise ValueError("real source and provisional video evidence required")
    race_id, day = str(manifest.get("raceId") or ""), _date(manifest.get("raceDate"))
    if not race_id or not day or race_id != config.get("raceId") or day != config.get("raceDate"):
        raise ValueError("video race identity mismatch")
    track = str(config.get("track") or "")
    number = config.get("raceNumber")
    if not track or type(number) is not int or not 1 <= number <= 12:
        raise ValueError("official race track and number required")
    ids = config.get("horseIdentityByNumber") or {}
    if not isinstance(ids, dict):
        raise ValueError("horse identity mapping must be a dictionary")
    seen = set()
    runners = {}
    for row in measured.get("runners") or []:
        if not isinstance(row, dict) or type(row.get("horseNumber")) is not int:
            raise ValueError("invalid measured runner")
        no = row["horseNumber"]
        if no <= 0 or no in seen:
            raise ValueError("duplicate measured runner")
        seen.add(no)
        # Need externally supplied stable horse ID to match the same horse
        # across races. A saddlecloth number is only unique within one race.
        stable_id = str(ids.get(str(no)) or "")
        if not stable_id:
            continue
        coverage = _measured(row.get("coverage"))
        speed = _measured(row.get("averageObservedSpeedMps"))
        distance_loss = _measured(row.get("distanceLossMeters"))
        if coverage is None or not 0 <= coverage <= 1:
            raise ValueError("invalid tracking coverage")
        # Automated OCR identity and distance are observational candidates,
        # not externally verified accuracy. Preserve this distinction.
        frames = manifest.get("frames") or []
        identities = {str(h.get("identitySource") or "")
                      for frame in frames for h in (frame.get("horses") or [])
                      if h.get("horseNumber") == no}
        kind = "externally-reviewed" if identities == {"externally-reviewed"} else (
            "automated-ocr-provisional" if "automated-ocr-provisional" in identities else "unconfirmed")
        runners[str(no)] = {
            "horseId": stable_id, "coverage": coverage,
            "validMovementSegments": int(row.get("validMovementSegments") or 0),
            "observedSpeedMps": speed,
            "observedPathMeters": _measured(row.get("observedPathMeters")),
            "distanceLossMeters": distance_loss,
            "possibleSlowdownEvents": len(row.get("possibleSlowdowns") or []),
            "identitySource": kind,
            "observationStatus": str(row.get("observationStatus") or ""),
        }
    return {
        "version": VERSION,
        "raceId": race_id, "raceDate": day, "track": track, "raceNumber": number,
        "videoSha256": source["sha256"], "modelSha256": manifest.get("model", {}).get("weightsSha256"),
        "evidenceHash": measured.get("evidenceHash"),
        "runners": runners,
        "predictionApplied": False,
        "verifiedForecastImprovement": False,
    }


def evidence_filename(race_id: str) -> str:
    if not race_id:
        raise ValueError("race identity required")
    return sha256(race_id.encode("utf-8")).hexdigest() + ".json"


def write_evidence(directory: str | Path, evidence: dict[str, Any]) -> Path:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / evidence_filename(str(evidence["raceId"]))
    if target.exists():
        prior = json.loads(target.read_text(encoding="utf-8"))
        if prior != evidence:
            raise ValueError("immutable video evidence already exists for race")
        return target
    # Write-before-rename makes partial outputs unavailable to readers.
    temp = destination / (target.name + ".pending")
    if temp.exists():
        raise ValueError("unfinished prior write requires investigation")
    temp.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(target)
    return target


def load_evidence(directory: str | Path, race_id: str) -> dict[str, Any] | None:
    target = Path(directory) / evidence_filename(race_id)
    if not target.is_file() or target.stat().st_size > 2_000_000:
        return None
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("version") != VERSION or data.get("raceId") != race_id:
        raise ValueError("vision cache race identity mismatch")
    return data


def attach_historical_video(detail: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Internal research-only data augmentation, no retrospective leakage.

    Only a full match of historical race/date/track/race-number AND stable
    horse ID is accepted. Never use current or future video as a pre-race
    feature, and never use result labels to change this identity match.
    """
    copied = deepcopy(detail)
    target_date = _date(detail.get("date"))
    if not target_date:
        raise ValueError("forecast date required")
    lookup = {}
    for entry in evidence:
        if not isinstance(entry, dict) or entry.get("version") != VERSION:
            continue
        day = _date(entry.get("raceDate"))
        if not day or day >= target_date:
            continue
        key = (str(entry.get("raceId") or ""), day)
        if not key[0] or key in lookup:
            raise ValueError("duplicate historical video evidence")
        lookup[key] = entry
    for horse in copied.get("horses") or []:
        if not isinstance(horse, dict):
            continue
        stable_id = str(horse.get("id") or "")
        matched = []
        for collection in ("allPastRuns", "recentRaces"):
            for run in horse.get(collection) or []:
                if not isinstance(run, dict):
                    continue
                day = _date(run.get("date") or run.get("raceDate"))
                race_id = str(run.get("raceId") or "")
                archive = lookup.get((race_id, day))
                if not archive or not stable_id or run.get("track") != archive.get("track"):
                    continue
                if str(run.get("raceNumber")) != str(archive.get("raceNumber")):
                    continue
                for no, row in archive.get("runners", {}).items():
                    if str(row.get("horseId") or "") != stable_id:
                        continue
                    value = {"raceId": race_id, "raceDate": day,
                             "horseNumber": int(no),
                             "videoSha256": archive["videoSha256"],
                             "identitySource": row.get("identitySource"),
                             "trackingCoverage": row.get("coverage"),
                             "observedSpeedMps": row.get("observedSpeedMps"),
                             "distanceLossMeters": row.get("distanceLossMeters"),
                             "possibleSlowdownEvents": row.get("possibleSlowdownEvents"),
                             "researchOnly": True}
                    run["visionResearch"] = value
                    if value not in matched:
                        matched.append(value)
        if matched:
            horse["visionResearchHistory"] = matched
    copied["visionResearchAppliedToProductionPrediction"] = False
    return copied
