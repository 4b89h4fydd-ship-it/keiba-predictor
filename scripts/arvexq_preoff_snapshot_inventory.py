#!/usr/bin/env python3
"""Read-only inventory of immutable-looking pre-off feature snapshots.

A sealed prediction timestamp is not proof that a saved feature snapshot was
captured before the race. Report those two kinds of evidence separately.
Never rewrite or promote these snapshots to verified pre-off training inputs.
"""
from __future__ import annotations
import base64
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path


def timestamp(value):
    try:
        t = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return t if t.tzinfo is not None else None
    except ValueError:
        return None


def inspect_envelope(envelope):
    if not isinstance(envelope, dict) or not envelope.get("gzipBase64"):
        return {"state": "not-compressed-snapshot"}
    raw = gzip.decompress(base64.b64decode(envelope["gzipBase64"]))
    if hashlib.sha256(raw).hexdigest() != envelope.get("sha256"):
        raise ValueError("snapshot SHA256 mismatch")
    race = json.loads(raw)
    if not isinstance(race, dict):
        return {"state": "not-race-object"}
    circuit = str(race.get("circuit") or "unknown")
    locked = isinstance(race.get("preRacePrediction"), dict)
    captured = timestamp(envelope.get("capturedAt") or envelope.get("savedAt"))
    race_date = str(race.get("date") or "")
    post_time = str(race.get("scheduledStartTime") or race.get("startTime") or "")
    try:
        post = timestamp(race_date + "T" + post_time[:5] + ":00+09:00")
    except (TypeError, ValueError):
        post = None
    # Only envelope-level snapshot time is considered; prediction fixedAt
    # cannot establish when mutable horse histories were actually captured.
    candidate = bool(captured and post and captured < post and
                     not race.get("result") and not race.get("payouts"))
    return {"state": "hash-valid", "circuit": circuit, "lockedForecast": locked,
            "candidate": candidate}


def main(root=Path("arvexq/ui/static/saved-snapshots")):
    counts = Counter()
    by_circuit = {}
    for path in sorted(root.glob("*.json")):
        try:
            item = inspect_envelope(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            counts["invalid"] += 1
            print("SNAPSHOT_INVALID", path.name, type(exc).__name__)
            continue
        state = item["state"]
        counts[state] += 1
        if state != "hash-valid":
            continue
        circuit = item["circuit"]
        box = by_circuit.setdefault(circuit, Counter())
        box["hashValid"] += 1
        counts["hashValid"] += 1
        if item["lockedForecast"]:
            box["sealedPredictionPresent"] += 1
            counts["sealedPredictionPresent"] += 1
        if item["candidate"]:
            box["preoffCaptureCandidates"] += 1
            counts["preoffCaptureCandidates"] += 1
    print("ARVEXQ_PREOFF_SNAPSHOT_INVENTORY=" + json.dumps({
        "counts": dict(counts), "byCircuit": {k:dict(v) for k,v in sorted(by_circuit.items())},
        "warning": "Capture candidates are not authenticated pre-off feature sets; no accuracy claim.",
    }, ensure_ascii=False))
    if counts["invalid"]:
        raise SystemExit("invalid archived snapshot integrity")


if __name__ == "__main__":
    main()
