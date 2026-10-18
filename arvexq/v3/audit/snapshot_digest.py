"""Offline bounded validation of ORIGINAL saved gzip JSON blobs.

No external network, no writes to repository data or database, and no model,
marks, odds forecasts, ticket suggestions or future-history restoration.
"""
from __future__ import annotations

import base64
import binascii
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zlib

from arvexq.v3.data.quality import normalize_circuit

DIGEST = re.compile(r"^[a-f0-9]{64}$")
MAX_UNCOMPRESSED = 16 * 1024 * 1024
MAX_COMPRESSED = 8 * 1024 * 1024


def _restore(blob: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    sha = expected.get("sha256")
    nbytes = expected.get("bytes")
    if not isinstance(sha, str) or not DIGEST.fullmatch(sha):
        raise ValueError("manifest-digest-invalid")
    if not isinstance(nbytes, int) or isinstance(nbytes, bool) or not 0 < nbytes <= MAX_UNCOMPRESSED:
        raise ValueError("manifest-size-invalid")
    if (blob.get("version") != "arvexq-saved-snapshot-v1"
            or blob.get("sha256") != sha or blob.get("bytes") != nbytes):
        raise ValueError("envelope-mismatch")
    encoded = blob.get("gzipBase64")
    if not isinstance(encoded, str) or len(encoded) > MAX_COMPRESSED * 2:
        raise ValueError("compressed-envelope-oversize")
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("base64-invalid") from exc
    if not compressed or len(compressed) > MAX_COMPRESSED:
        raise ValueError("compressed-size-invalid")
    try:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        restored = decoder.decompress(compressed, MAX_UNCOMPRESSED + 1)
        if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
                or len(restored) > MAX_UNCOMPRESSED):
            raise ValueError("gzip-invalid-or-unbounded")
        restored += decoder.flush()
    except zlib.error as exc:
        raise ValueError("gzip-invalid") from exc
    if len(restored) != nbytes or hashlib.sha256(restored).hexdigest() != sha:
        raise ValueError("sha256-or-length-mismatch")
    try:
        obj = json.loads(restored.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("restored-json-invalid") from exc
    if not isinstance(obj, dict):
        raise ValueError("restored-race-not-object")
    return obj


def verify_one(directory: Path, race_id: str, expected: dict[str, Any],
               *, day: str, circuit: str, card_horses: list[dict[str, Any]], verify_history: bool = False) -> dict[str, Any]:
    """Exactly one deterministic local blob. Return verification metadata only."""
    if not isinstance(expected, dict):
        raise ValueError("manifest-record-not-object")
    sha = expected.get("sha256")
    if not isinstance(sha, str) or not DIGEST.fullmatch(sha) or expected.get("file") != sha + ".json":
        raise ValueError("manifest-filename-invalid")
    fp = directory / (sha + ".json")
    if not fp.is_file():
        raise ValueError("snapshot-payload-file-missing")
    if fp.stat().st_size > MAX_COMPRESSED * 2 + 10000:
        raise ValueError("snapshot-envelope-file-oversize")
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("snapshot-envelope-json-invalid") from exc
    if not isinstance(raw, dict):
        raise ValueError("snapshot-envelope-not-object")
    restored = _restore(raw, expected)
    if restored.get("id") != race_id or restored.get("date") != day:
        raise ValueError("snapshot-identity-or-date-mismatch")
    if normalize_circuit(restored.get("circuit")) != circuit:
        raise ValueError("snapshot-circuit-mismatch")
    horses = restored.get("horses")
    if not isinstance(horses, list) or len(horses) != len(card_horses):
        raise ValueError("snapshot-runner-count-mismatch")
    if not isinstance(expected.get("horses"), int) or expected["horses"] != len(horses):
        raise ValueError("manifest-runner-count-mismatch")

    def identities(rows: list[dict[str, Any]]) -> dict[int, str]:
        result: dict[int, str] = {}
        for h in rows:
            if not isinstance(h, dict):
                raise ValueError("invalid-runner-row")
            no = h.get("horseNumber")
            name = h.get("name")
            if not isinstance(no, int) or isinstance(no, bool) or no <= 0 or no in result:
                raise ValueError("invalid-runner-number")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("missing-runner-name")
            result[no] = name.strip()
        return result

    if identities(horses) != identities(card_horses):
        raise ValueError("snapshot-runner-identity-mismatch")
    report = {"raceId": race_id, "circuit": circuit, "status": "verified",
              "sha256": sha, "restoredBytes": expected["bytes"], "runnerRows": len(horses)}
    if verify_history:
        # Existing archive recovery is hash/size bounded. It NEVER proves that
        # the recorded starts cover an entire racing career.
        from arvexq.ingest.career_transport import recover_horse
        from arvexq.ingest.full_career import merge_career, date_key
        from arvexq.v3.audit.runner_gaps import classify_absent_prior, compare_saved_weight
        with_prior = 0
        prior_rows = 0
        archive_count = 0
        future_rows = 0
        invalid_dates = 0
        no_prior_cases = []
        weight_issues = []
        card_by_number = {h["horseNumber"]: h for h in card_horses}
        for h in horses:
            archive_count += isinstance(h.get("careerArchive"), dict)
            recovered = recover_horse(h, day)
            runs = merge_career(recovered.get("allPastRuns"), recovered.get("recentRaces"), day)
            prior_rows += len(runs)
            with_prior += bool(runs)
            if not runs:
                no_prior_cases.append(classify_absent_prior(recovered, restored))
            weight_issue = compare_saved_weight(card_by_number[h["horseNumber"]], h, restored)
            if weight_issue is not None:
                weight_issues.append(weight_issue)
            for key in ("allPastRuns", "recentRaces"):
                for row in h.get(key) or []:
                    if not isinstance(row, dict):
                        continue
                    at = date_key(row.get("date") or row.get("raceDate") or row.get("日付"))
                    invalid_dates += not bool(at)
                    future_rows += bool(at and at >= day)
        report["historyAudit"] = {
            "careerSidecarsVerified": archive_count,
            "runnersWithObservedPriorRuns": with_prior,
            "observedPriorRunRows": prior_rows,
            "sameOrFutureDirectRows": future_rows,
            "invalidDirectDateRows": invalid_dates,
            "lifetimeCompleteness": "unverified",
            "noObservedPriorCases": no_prior_cases,
            "missingCardWeightCases": weight_issues,
        }
    return report


def select_samples(card: dict[str, Any], manifest: dict[str, Any],
                   *, per_circuit: int = 2) -> list[tuple[str, str, dict[str, Any], list[dict[str, Any]]]]:
    if not isinstance(per_circuit, int) or isinstance(per_circuit, bool) or not 1 <= per_circuit <= 6:
        raise ValueError("samples-per-circuit must be 1..6")
    if not isinstance(card, dict) or not isinstance(manifest, dict) or card.get("date") != manifest.get("date"):
        raise ValueError("archive date mismatch")
    rows = card.get("races")
    saved = manifest.get("races")
    if not isinstance(rows, list) or not isinstance(saved, dict):
        raise ValueError("invalid card/manifest collections")
    by_circuit: dict[str, list[dict[str, Any]]] = {"jra": [], "nar": []}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid race row")
        circuit = normalize_circuit(row.get("circuit"))
        rid = str(row.get("id") or "")
        if circuit not in by_circuit or not rid.startswith(circuit + "-"):
            raise ValueError("unknown or contradictory race circuit")
        by_circuit[circuit].append(row)
    output = []
    for circuit, candidates in by_circuit.items():
        ordered = sorted(candidates, key=lambda x: x["id"])
        # Across the ID range, not random and not a representative estimate.
        if not ordered:
            continue
        picks = ([ordered[0]] if per_circuit == 1 else
                 [ordered[(i * (len(ordered) - 1)) // (per_circuit - 1)]
                  for i in range(per_circuit)])
        seen: set[str] = set()
        for row in picks:
            rid = row["id"]
            if rid in seen:
                continue
            seen.add(rid)
            if rid not in saved:
                raise ValueError("missing-saved-manifest-race")
            output.append((rid, circuit, saved[rid], row.get("horses") or []))
    return output


def audit_saved_blobs(directory: Path, card: dict, manifest: dict,
                      *, per_circuit: int = 2) -> dict:
    samples = select_samples(card, manifest, per_circuit=per_circuit)
    rows, counts = [], {"jra": Counter(), "nar": Counter()}
    for rid, circuit, record, runners in samples:
        try:
            verified = verify_one(directory / "saved-snapshots", rid, record,
                                  day=card["date"], circuit=circuit, card_horses=runners)
        except (ValueError, OSError) as exc:
            verified = {"raceId": rid, "circuit": circuit, "status": "failed",
                        "errorCode": str(exc)[:90]}
        counts[circuit]["checked"] += 1
        counts[circuit]["verified" if verified["status"] == "verified" else "failed"] += 1
        rows.append(verified)
    return {
        "schema": "arvexq-v3-snapshot-sha256-sample-audit-1",
        "date": card["date"],
        "sampling": "deterministic-spaced-race-id, not random or exhaustive",
        "perCircuitLimit": per_circuit,
        "counts": {k: dict(v) for k, v in counts.items()},
        "samples": rows,
        "allSampledVerified": bool(rows) and all(r["status"] == "verified" for r in rows),
        "fullArchiveVerified": False,
        "officialRaceCompletenessVerified": False,
        "predictionStatus": "not-implemented",
    }
