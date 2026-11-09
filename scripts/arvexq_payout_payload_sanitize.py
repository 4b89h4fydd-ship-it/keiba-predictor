#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Make a result-repair payload syncable without losing feature data.

Companion to the one-off payout-duplicate repair workflow. A repaired
historical detail can carry a raw massFeatureSnapshot whose pre-race
prediction twin is not part of the repair payload (it lives in the
stored publication, which the protect seam restores at write time).
``pack_detail`` refuses to archive such a matrix, and one refusal kills
the whole day's sync batches (2026-11-09: the 2026-10-03 and 2026-10-04
repairs were fully built and silently never posted).

For each payload detail this script therefore tries, in order:

1. ``pack_detail`` as-is — the normal case, nothing changes.
2. Convert the raw snapshot to its canonical archive form
   (``massFeatureArchive``). The conversion is accepted ONLY when the
   archive builds under the strict origin-hash check, its feature hash
   equals the detail's declared ``massFeatureHash``, and recovering the
   archive reproduces the snapshot exactly — a lossless-or-nothing
   rewrite; readers restore the snapshot from the archive on demand.
3. If a detail still cannot pack, drop THAT detail from the payload
   (its summary stays, so the race simply remains unrepaired) and
   report it, instead of losing the whole day.

Every conversion and drop is printed; nothing is dropped silently.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.ingest.career_transport import pack_detail  # noqa: E402
from arvexq.prediction.mass_feature_transport import (  # noqa: E402
    archive_snapshot,
    recover_mass_detail,
)

MASS_ERROR = "cannot archive mass feature matrix without pre-off forecast"


def _packable(detail: dict[str, Any]) -> str:
    try:
        pack_detail(copy.deepcopy(detail))
        return ""
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _convert_snapshot(detail: dict[str, Any]) -> dict[str, Any] | None:
    snapshot = detail.get("massFeatureSnapshot")
    if not isinstance(snapshot, dict):
        return None
    try:
        archive = archive_snapshot(
            snapshot,
            race_id=str(detail.get("id") or ""),
            race_date=str(detail.get("date") or ""),
            preserve_unverified_legacy=False)
    except Exception:
        return None
    declared = detail.get("massFeatureHash")
    if declared and archive.get("featureHash") != declared:
        return None
    converted = copy.deepcopy(detail)
    converted.pop("massFeatureSnapshot", None)
    converted["massFeatureArchive"] = archive
    try:
        recovered = recover_mass_detail(copy.deepcopy(converted))
    except Exception:
        return None
    if recovered.get("massFeatureSnapshot") != snapshot:
        return None
    return converted


def sanitize(payload: dict[str, Any]) -> dict[str, Any]:
    details = payload.get("details") or []
    kept: list[dict[str, Any]] = []
    converted_ids: list[str] = []
    dropped: list[tuple[str, str]] = []
    for detail in details:
        if not isinstance(detail, dict):
            continue
        rid = str(detail.get("id") or "")
        error = _packable(detail)
        if not error:
            kept.append(detail)
            continue
        if MASS_ERROR in error:
            converted = _convert_snapshot(detail)
            if converted is not None and not _packable(converted):
                kept.append(converted)
                converted_ids.append(rid)
                print("SANITIZE_CONVERTED", rid)
                continue
        dropped.append((rid, error))
        print("SANITIZE_DROPPED", rid, error)
    payload["details"] = kept
    print(f"SANITIZE_SUMMARY kept={len(kept)} converted={len(converted_ids)} "
          f"dropped={len(dropped)}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    path = Path(args.payload)
    payload = json.loads(path.read_text(encoding="utf-8"))
    sanitize(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
