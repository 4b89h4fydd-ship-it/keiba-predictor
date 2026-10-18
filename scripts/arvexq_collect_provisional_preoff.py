#!/usr/bin/env python3
"""Scheduled, read-only provisional pre-off evidence collector.

Uses ONLY the existing Cloudflare race-data API. Its roster originates from
that same API, not an independently verified official source. Accordingly
records are explicitly NOT eligible for certified model training.
No legacy prediction/marks/bets calls, no /api/sync, and no D1 writes.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import gzip
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from arvexq.prediction.mass_feature_snapshot import build_mass_feature_snapshot

JST = timezone(timedelta(hours=9))
API_BASE = "https://kraiz-api.4b89h4fydd.workers.dev"
VERSION = "arvexq-provisional-preoff-collection-v1"
SCRATCH_WORDS = ("取消", "除外", "欠場", "SCRATCHED", "WITHDRAWN")


def _get_json(url):
    req = Request(url, headers={"accept": "application/json",
                                "cache-control": "no-cache",
                                "user-agent": "ARVEXQ-PreOff-Research-Collector/1"})
    with urlopen(req, timeout=12) as response:
        data = response.read(8_000_001)
    if len(data) > 8_000_000:
        raise ValueError("API response larger than 8MB")
    obj = json.loads(data)
    if not isinstance(obj, dict) or obj.get("ok") is False:
        raise ValueError("invalid race API response")
    return obj


def _post_at(race):
    day = race.get("date")
    clock = race.get("startTime") or race.get("scheduledStartTime")
    if not isinstance(day, str) or not isinstance(clock, str):
        raise ValueError("race post time missing")
    try:
        return datetime.strptime(day + " " + clock[:5],
                                 "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    except ValueError:
        raise ValueError("invalid scheduled post time") from None


def _active_roster(detail):
    horses = detail.get("horses")
    if not isinstance(horses, list):
        raise ValueError("missing race field")
    found = set()
    active = []
    for horse in horses:
        if not isinstance(horse, dict) or type(horse.get("horseNumber")) is not int:
            raise ValueError("unreconciled runner identity")
        n = horse["horseNumber"]
        if n <= 0 or n in found:
            raise ValueError("invalid or duplicate runner identity")
        found.add(n)
        status = str(horse.get("status") or "").upper()
        inactive = (any(horse.get(key) for key in ("scratched","withdrawn","cancelled"))
                    or any(word in status for word in SCRATCH_WORDS))
        if not inactive:
            if not str(horse.get("name") or "").strip():
                raise ValueError("unnamed active runner")
            active.append(horse)
    if len(active) < 3:
        raise ValueError("insufficient active field")
    return active


def provisional_capture(detail, *, now):
    """Build a pre-post immutable artifact, without claiming official attestation."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("timezone-aware capture time required")
    if not isinstance(detail, dict) or not detail.get("id"):
        raise ValueError("race identity missing")
    # API may send empty result placeholders before post. Non-empty outcome
    # fields are always rejected, never reinterpreted as pre-off evidence.
    if any(detail.get(key) not in (None, {}, [], "") for key in
           ("result", "results", "payouts")):
        raise ValueError("non-empty post-race fields prohibited")
    post = _post_at(detail)
    if not now < post:
        raise ValueError("post time already passed")
    active = _active_roster(detail)
    filtered = deepcopy(detail)
    filtered["horses"] = deepcopy(active)
    for horse in filtered["horses"]:
        if any(k in horse for k in ("currentResult","finishPosition","raceResult","payout")):
            raise ValueError("current race outcome may not enter snapshot")
        for k in ("mark","predMark","integratedEvaluation","honmeiRole",
                  "modelProbabilities","betRecommendations","preRacePrediction",
                  "aiEvaluation","factorRanking","abilityRanking"):
            horse.pop(k, None)
    for k in ("result", "results", "payouts", "preRacePrediction","preRaceBet","aiEvaluation","factorRanking",
              "abilityRanking","honmeiDecision","massFeatureSnapshot",
              "massFeatureArchive"):
        filtered.pop(k, None)
    snapshot = build_mass_feature_snapshot(filtered)
    numbers = [h["horseNumber"] for h in active]
    if (snapshot.get("horseCount") != len(numbers)
            or {r.get("horseNumber") for r in snapshot.get("rows", [])} != set(numbers)):
        raise ValueError("frozen field mismatch")
    history_count = sum(bool(h.get("recentRaces") or h.get("allPastRuns"))
                        for h in active)
    record = {
        "horsesWithPastRuns": history_count,
        "historyComplete": history_count == len(active),
        "version": VERSION, "eligibility": "provisional-not-officially-attested",
        "source": "existing-cloudflare-race-api", "independentOfficialRoster": False,
        "raceId": snapshot["raceId"], "featureHash": snapshot["featureHash"],
        "activeHorseNumbers": numbers, "capturedAtEpoch": int(now.timestamp()),
        "postAtEpoch": int(post.timestamp()), "snapshot": snapshot,
    }
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                     allow_nan=False).encode("utf-8")
    record["recordHash"] = sha256(raw).hexdigest()
    return record


def collect(*, base=API_BASE, now=None, ahead_minutes=35, max_races=12,
            fetch=None):
    clock = (now or datetime.now(JST)).astimezone(JST)
    if ahead_minutes < 1 or max_races < 1:
        raise ValueError("positive collection window required")
    fetcher = fetch or _get_json
    root = base.rstrip("/")
    if root != API_BASE:
        raise ValueError("only existing production read-only API allowed")
    day = clock.date().isoformat()
    overview = fetcher(root + "/api/day?date=" + day + "&details=0")
    candidates = overview.get("races")
    if not isinstance(candidates, list):
        raise ValueError("missing day roster")
    due = []
    for row in candidates:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        try:
            mins = (_post_at(row) - clock).total_seconds() / 60
        except ValueError:
            continue
        if 0 < mins <= ahead_minutes:
            due.append(row)
    due.sort(key=lambda x: (x.get("startTime") or "", str(x["id"])))
    due = due[:max_races]
    artifacts, failures = [], []
    # Only existing Cloudflare API routes; never a second provider or a
    # fabricated race ID. Compact /api/racecard is NOT sufficient history.
    fallback = None
    for row in due:
        rid = str(row["id"])
        try:
            detail = None
            errors = []
            # The legacy endpoint may be absent for a race for which the D1
            # display endpoint still has the full stored history.
            for suffix in ("", "?view=display"):
                path = root + "/api/race/" + quote(rid, safe="") + suffix
                try:
                    body = fetcher(path)
                except Exception as exc:
                    if getattr(exc, "code", None) == 404:
                        errors.append("not-found")
                        continue
                    raise
                candidate = body.get("detail")
                if isinstance(candidate, dict) and str(candidate.get("id")) == rid:
                    detail = candidate
                else:
                    errors.append("missing-or-wrong-identity")
            if detail is None:
                # A same-source day response is the final full-history
                # fallback. Never reuse a different race's payload.
                if fallback is None:
                    fallback = fetcher(root + "/api/day?date=" + day + "&details=1")
                details = fallback.get("details") or []
                detail = next((x for x in details if isinstance(x, dict)
                               and str(x.get("id")) == rid), None)
            if not isinstance(detail, dict) or str(detail.get("id")) != rid:
                raise ValueError("no matching full race detail in existing API")
            if str(detail.get("date")) != str(row.get("date")):
                raise ValueError("race dates disagree")
            if _post_at(detail) != _post_at(row):
                raise ValueError("race scheduled post changed across endpoints")
            record = provisional_capture(detail, now=clock)
            artifacts.append(record)
        except (ValueError, KeyError, TypeError, TimeoutError, OSError) as exc:
            failures.append({"raceId": rid, "errorType": type(exc).__name__,
                             "reason": str(exc)[:140]})
    return {"version": VERSION, "date": day, "capturedAtEpoch": int(clock.timestamp()),
            "candidates": len(due), "captured": len(artifacts),
            "records": artifacts, "failures": failures,
            "verifiedForTraining": False}


def write_bundle(bundle, dest):
    """No overwrite, no post-hoc rewriting of a saved artifact."""
    data = json.dumps(bundle, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    compressed = gzip.compress(data, compresslevel=9, mtime=0)
    output = Path(dest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as fp:
        fp.write(compressed)
    return {"path": str(output), "rawBytes": len(data),
            "compressedBytes": len(compressed), "sha256": sha256(compressed).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("preoff-research-capture"))
    parser.add_argument("--ahead-minutes", type=int, default=35)
    parser.add_argument("--max-races", type=int, default=12)
    args = parser.parse_args()
    data = collect(ahead_minutes=args.ahead_minutes, max_races=args.max_races)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    result = write_bundle(data, args.out_dir / ("provisional-" + stamp + ".json.gz"))
    print(json.dumps({**result, "captured": data["captured"], "candidates": data["candidates"],
                      "failures": data["failures"], "trainingEligible": False},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
