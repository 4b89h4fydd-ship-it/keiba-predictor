#!/usr/bin/env python3
"""Apply the one-condition authorization patch to the LIVE kraiz-api bundle.

Background (2026-10-31, see delivery-transform-topology-20261031.md):
the deployed kraiz-api worker is a single-module bundle
(worker-entry-overlay.js) that is NOT reproducible from this repository.
Its request-time `publicRace()` gate (`authorizedStage64`) authorizes a
race detail only when `prediction.modelVersion` is exactly
"arvexq-stage64-product-v1". Stage64 was retired (PR #501); the sole
production engine is now "arvexq-rewrite-v1-uncalibrated-prior", so every
current race detail is rewritten to predictionStatus='disabled' with
recommendedBets stripped at delivery time, even though the stored D1
payload is healthy ('ready' + full ticket groups).

This patch widens that ONE condition to accept the current production
model version as well. Every other gate condition is untouched:

Update (2026-11-01): the v8 candidate (margin-weighted Elo + speed
index v2) was adopted into the production publish lane after its
first forward verdict, and the publish model version moved to
"arvexq-rewrite-v2-elo-speed2". The allowlist therefore accepts all
three versions: the retired Stage64 (historical payloads), the v1
rewrite engine (payloads published through 2026-11-01), and v2.
Nothing else about the gate changes.
predictionStatus 'ready' at both levels, productionEligible === true,
raceId/date match, and predictionMarks must be exactly the five marks
◎○▲△☆ in order with valid, unique horse numbers.

Usage:
  python3 patch_live_bundle.py <downloaded-bundle.js> <output-patched.js>

The anchor must occur exactly once; otherwise the script refuses.
Idempotent: an already-patched bundle is reported and copied unchanged
only if --force is given (default: refuse, to avoid silent double work).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ANCHOR = 'p.modelVersion !== "arvexq-stage64-product-v1"'
REPLACEMENT = (
    '!["arvexq-stage64-product-v1", '
    '"arvexq-rewrite-v1-uncalibrated-prior", '
    '"arvexq-rewrite-v2-elo-speed2"].includes(p.modelVersion)'
)
PATCH_MARKER = '"arvexq-rewrite-v2-elo-speed2"].includes(p.modelVersion)'


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    source = src_path.read_text(encoding="utf-8")
    if PATCH_MARKER in source:
        print("ALREADY_PATCHED: bundle already authorizes the rewrite model")
        return 1
    count = source.count(ANCHOR)
    if count != 1:
        print(f"ANCHOR_COUNT={count} (expected exactly 1); refusing to patch")
        return 1
    patched = source.replace(ANCHOR, REPLACEMENT)
    out_path.write_text(patched, encoding="utf-8")
    print("PATCHED_OK")
    print("source_sha256:", hashlib.sha256(source.encode()).hexdigest())
    print("patched_sha256:", hashlib.sha256(patched.encode()).hexdigest())
    print("source_bytes:", len(source.encode()), "patched_bytes:", len(patched.encode()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
