#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Split ARVEXQ /api/sync payloads into small race-scoped batches.

Cloudflare rejects the previous 150+ MB all-day payloads.  This helper keeps
replace-upserts safe by pairing each rich detail with its matching summary and
only sends unmatched summaries/odds in compact follow-up batches.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arvexq.ingest.career_transport import pack_detail
from scripts.arvexq_detail_size_audit import print_size_audit


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"sync payload must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> int:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    return len(raw)


def race_id(row: Any) -> str:
    return str(row.get("id") or "") if isinstance(row, dict) else ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--odds-rows-per-batch", type=int, default=250)
    args = p.parse_args()

    payload = load_json(Path(args.input))
    summaries = [x for x in (payload.get("summaries") or []) if isinstance(x, dict)]
    source_details = [x for x in (payload.get("details") or []) if isinstance(x, dict) and race_id(x)]
    # Live deltas can contain old D1 snapshots whose feature hash was
    # already inconsistent before this run. Preserve bytes, mark them
    # unverified, and disallow subsequent training instead of fabricating.
    live_delta = bool((payload.get("meta") or {}).get("live_delta"))
    details = [pack_detail(x, preserve_unverified_legacy=live_delta)
               for x in source_details]
    unverified = [
        race_id(d) for d in details
        if (d.get("massFeatureArchive") or {}).get("originHashVerified") is False
    ]
    if unverified:
        print("MASS_FEATURE_LEGACY_UNVERIFIED",
              "count="+str(len(unverified)), "races="+",".join(unverified[:10]),
              "training_eligible=false")
    raw_mass_bytes = sum(len(json.dumps(d.get("massFeatureSnapshot"), ensure_ascii=False,
                                        separators=(",", ":"), default=str).encode("utf-8"))
                         for d in source_details if isinstance(d.get("massFeatureSnapshot"), dict))
    archive_mass_bytes = sum(len(json.dumps(d.get("massFeatureArchive"), ensure_ascii=False,
                                            separators=(",", ":"), default=str).encode("utf-8"))
                             for d in details if isinstance(d.get("massFeatureArchive"), dict))
    archived_mass_count = sum(bool(d.get("massFeatureArchive")) for d in details)
    for original, prepared in zip(source_details, details):
        if isinstance(original.get("massFeatureSnapshot"), dict):
            if not prepared.get("massFeatureArchive") or prepared.get("massFeatureSnapshot"):
                raise SystemExit("D1 mass-feature transfer must be lossless and archive-only")
    career_starts = sum(int((h.get("careerTransport") or {}).get("observedRuns") or 0)
                        for d in details for h in (d.get("horses") or []) if isinstance(h, dict))
    source_bytes = Path(args.input).stat().st_size
    # D1 currently permits at most 2,000,000 bytes per string/BLOB/row.
    # The Worker storage schema lives outside this repository, so log potential
    # violations; never drop a race or its career archive to hide the problem.
    row_risks = []
    for detail in details:
        row_size = print_size_audit(detail, max_detail_bytes=1_500_000)["totalBytes"]
        if row_size > 1_800_000:
            row_risks.append((race_id(detail), row_size))
            print("D1_DETAIL_ROW_SIZE_RISK", "race="+race_id(detail),
                  "bytes="+str(row_size), "limit_if_one_row=2000000")
    odds = [x for x in (payload.get("odds_current") or []) if isinstance(x, dict)]
    meta = dict(payload.get("meta") or {})

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()

    summary_by_id = {race_id(x): x for x in summaries if race_id(x)}
    consumed_summary_ids: set[str] = set()
    batch_no = 0
    total_bytes = 0
    largest = 0

    def emit(body: dict[str, Any], kind: str) -> None:
        nonlocal batch_no, total_bytes, largest
        batch_no += 1
        body_meta = dict(meta)
        body_meta.update({
            "sync_batch": True,
            "sync_batch_index": batch_no,
            "sync_batch_kind": kind,
        })
        body["meta"] = body_meta
        path = out_dir / f"batch-{batch_no:04d}.json"
        size = write_json(path, body)
        total_bytes += size
        largest = max(largest, size)
        print(f"SYNC_BATCH {path} kind={kind} bytes={size}")

    # Rich details dominate payload size. Send one race at a time so a single
    # oversized day can never trip Cloudflare's request-body limit.
    for detail in details:
        rid = race_id(detail)
        body: dict[str, Any] = {
            "summaries": [summary_by_id[rid]] if rid in summary_by_id else [],
            "details": [detail],
        }
        if rid in summary_by_id:
            consumed_summary_ids.add(rid)
        emit(body, "detail")

    # Summaries that have no detail yet are still important for the race list.
    remaining_summaries = [
        row for row in summaries
        if race_id(row) not in consumed_summary_ids
    ]
    if remaining_summaries:
        emit({"summaries": remaining_summaries, "details": []}, "summaries")

    # Live odds are compact but can still be numerous. Keep them separate so
    # detail replacement and market refresh cannot make one giant request.
    step = max(1, int(args.odds_rows_per_batch))
    for i in range(0, len(odds), step):
        emit({"summaries": [], "details": [], "odds_current": odds[i:i + step]}, "odds")

    if batch_no == 0:
        emit({"summaries": [], "details": []}, "empty")

    print("MASS_FEATURE_TRANSFER_AUDIT",
          f"archived_races={archived_mass_count}",
          f"raw_bytes={raw_mass_bytes}",
          f"archive_bytes={archive_mass_bytes}",
          f"ratio={archive_mass_bytes / max(1, raw_mass_bytes):.3f}")
    print("CAREER_TRANSFER_AUDIT", f"career_starts={career_starts}",
          f"uncompressed_input_bytes={source_bytes}",
          f"packed_batches_bytes={total_bytes}",
          f"transfer_ratio={total_bytes / max(1, source_bytes):.3f}")
    print(
        "SYNC_BATCH_AUDIT",
        f"batches={batch_no}",
        f"details={len(details)}",
        f"summaries={len(summaries)}",
        f"odds={len(odds)}",
        f"largest_bytes={largest}",
        f"detail_row_risks={len(row_risks)}",
        f"total_bytes={total_bytes}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
