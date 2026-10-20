"""Bounded, independently hash-verified restore of saved factual snapshot originals.

Reads only existing local content-addressed files; never rewrites source or
promotes archived preoff prediction, marks or bet receipts to present forecasts.
"""
from __future__ import annotations

import base64
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

from arvexq.ingest.full_career import merge_career
from arvexq.ingest.full_career import date_key

SHA256 = re.compile(r"^[a-f0-9]{64}$")
MAX_RAW_BYTES = 100_000_000
MAX_COMPRESSED_BYTES = 12_000_000


def verify_saved_payload(root: Path, card: dict[str, Any],
                         reference: dict[str, Any]) -> dict[str, Any]:
    """Verify one immutable saved original and its roster against an existing card.

    Returns only aggregates, no original scoring, betting or personal horse
    details. Does not assert lifetime history is complete.
    """
    race_id = str(card.get("id") or "")
    day = str(card.get("date") or "")
    token = reference.get("sha256")
    filename = reference.get("file")
    if not isinstance(token, str) or not SHA256.fullmatch(token) or filename != token + ".json":
        raise ValueError("invalid immutable snapshot digest/name")
    path = root / filename
    if not path.is_file():
        raise ValueError("missing immutable snapshot payload")
    if path.stat().st_size > MAX_COMPRESSED_BYTES:
        raise ValueError("envelope exceeds size limit")
    env = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(env, dict) or env.get("version") != "arvexq-saved-snapshot-v1"
        or env.get("sha256") != token or env.get("bytes") != reference.get("bytes")):
        raise ValueError("immutable snapshot envelope mismatch")
    size = env["bytes"]
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_RAW_BYTES:
        raise ValueError("unsafe snapshot output bytes")
    try:
        zipped = base64.b64decode(env["gzipBase64"], validate=True)
        if len(zipped) > MAX_COMPRESSED_BYTES:
            raise ValueError("snapshot compressed data too large")
        with gzip.GzipFile(fileobj=io.BytesIO(zipped), mode="rb") as f:
            payload = f.read(size + 1)
    except (OSError, EOFError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("snapshot restore invalid: " + type(exc).__name__) from exc
    if len(payload) != size:
        raise ValueError("restored snapshot size mismatch")
    if hashlib.sha256(payload).hexdigest() != token:
        raise ValueError("restored snapshot digest mismatch")
    try:
        original = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("restored snapshot JSON invalid") from exc
    if not isinstance(original, dict) or original.get("id") != race_id or original.get("date") != day:
        raise ValueError("restored race identity mismatch")
    horses = original.get("horses")
    card_horses = card.get("horses")
    if not isinstance(horses, list) or not isinstance(card_horses, list):
        raise ValueError("original runner roster missing")
    if len(horses) != len(card_horses) or len(horses) != reference.get("horses"):
        raise ValueError("saved original/card runner count mismatch")
    def identities(rows):
        seen = set()
        for h in rows:
            if not isinstance(h, dict):
                raise ValueError("invalid original runner row")
            no = h.get("horseNumber")
            name = "".join(str(h.get("name") or "").split())
            if not isinstance(no, int) or isinstance(no, bool) or no <= 0 or not name or no in seen:
                raise ValueError("invalid/duplicate original horse identity")
            seen.add(no)
        return seen
    if identities(horses) != identities(card_horses):
        raise ValueError("saved original/card runner identity mismatch")

    with_prior = 0
    observed_prior = 0
    for h in horses:
        # Compressed sidecar histories are separate and not decoded here. Only
        # directly observed dated rows are counted, never fabricated as complete.
        runs = merge_career(h.get("allPastRuns"), h.get("recentRaces"), day)
        observed_prior += len(runs)
        with_prior += bool(runs)
    return {
        "raceId": race_id,
        "circuit": "jra" if race_id.startswith("jra-") else "nar",
        "hashVerified": True,
        "rosterCount": len(horses),
        "runnersWithDirectPriorRuns": with_prior,
        "directPriorRunRows": observed_prior,
        "fullCareerVerified": False,
        "predictionStatus": "not-implemented",
    }


def sample_saved_payloads(directory: Path, reports: list[dict],
                          samples_per_circuit: int = 1) -> dict[str, Any]:
    if not 0 <= samples_per_circuit <= 10:
        raise ValueError("samples_per_circuit must be 0..10")
    summary = {"sampledPayloads": 0, "verifiedPayloads": 0,
               "observedDirectPriorRunRows": 0,
               "runnersWithDirectPriorRuns": 0,
               "failures": [], "samples": [],
               "fullCareerVerified": False}
    if samples_per_circuit == 0:
        return summary
    for report in reports:
        day = report["date"]
        card_file = directory / "racecards" / (day + ".json")
        man_file = directory / "saved-snapshots" / (day + ".json")
        card = json.loads(card_file.read_text(encoding="utf-8"))
        refs = json.loads(man_file.read_text(encoding="utf-8"))["races"]
        by_id = {r["id"]: r for r in card["races"]}
        for circuit in ("jra", "nar"):
            items = [(rid, ref) for rid, ref in refs.items()
                     if rid.startswith(circuit + "-") and rid in by_id
                     and isinstance(ref, dict)]
            items.sort(key=lambda pair: (pair[1].get("bytes") if isinstance(
                pair[1].get("bytes"), int) else 0, pair[0]))
            if not items:
                continue
            # Median by saved size avoids selecting only empty small debut
            # races; still a sample, never the full population.
            count = min(len(items), samples_per_circuit)
            selected = [items[(i+1)*len(items)//(count+1)] for i in range(count)]
            for rid, ref in selected:
                summary["sampledPayloads"] += 1
                try:
                    item = verify_saved_payload(directory / "saved-snapshots", by_id[rid], ref)
                    summary["verifiedPayloads"] += 1
                    summary["observedDirectPriorRunRows"] += item["directPriorRunRows"]
                    summary["runnersWithDirectPriorRuns"] += item["runnersWithDirectPriorRuns"]
                    summary["samples"].append(item)
                except (ValueError, OSError, json.JSONDecodeError) as exc:
                    summary["failures"].append({"raceId": rid,
                        "error": type(exc).__name__ + ": " + str(exc)[:160]})
    return summary
