"""Opt-in D1 transport for an independently archived, still-pre-off snapshot.

Disabled by default. No old predictions, marks or tickets. Raw strings preserve
the exact Python JSON canonical hashes across Python/JavaScript runtimes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib import request
import json
import os
import gzip

from arvexq.forecast.preoff_evidence_store import canonical, read_capture

DEFAULT_ENDPOINT = "https://kraiz-api.4b89h4fydd.workers.dev/api/research/preoff-evidence"


def prepare_payload(record):
    snapshot, receipt = record["snapshot"], record["receipt"]
    return {
        "snapshot": snapshot,
        "receipt": receipt,
        "snapshotCoreCanonical": canonical({
            k: v for k, v in snapshot.items() if k != "featureHash"
        }).decode("utf-8"),
        "receiptCoreCanonical": canonical({
            k: v for k, v in receipt.items() if k != "receiptHash"
        }).decode("utf-8"),
    }


def upload_capture(connection, capture_id, *, endpoint=DEFAULT_ENDPOINT,
                   token=None, clock=None, transport=None):
    """Send once only while the original pre-off evidence is fresh.

    A later retry is explicitly rejected, even if the record was correctly
    captured before post. The independently recorded evidence remains locally.
    """
    if os.environ.get("ARVEXQ_ENABLE_PREOFF_D1_CAPTURE") != "1":
        raise ValueError("pre-off D1 capture is disabled")
    secret = token if token is not None else os.environ.get("FORECAST_CAPTURE_TOKEN", "")
    if not isinstance(secret, str) or len(secret) < 24:
        raise ValueError("dedicated pre-off capture token unavailable")
    if endpoint != DEFAULT_ENDPOINT:
        raise ValueError("only the pinned Cloudflare capture endpoint is accepted")
    record = read_capture(connection, capture_id)
    now = clock if clock is not None else int(datetime.now(timezone.utc).timestamp())
    if type(now) is not int:
        raise ValueError("integer server clock required")
    receipt = record["receipt"]
    if not (receipt["capturedAtEpoch"] <= now < receipt["postAtEpoch"]
            and now - receipt["capturedAtEpoch"] <= 300):
        raise ValueError("cannot upload stale or post-off evidence")
    payload = json.dumps(prepare_payload(record), ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    # Compress the complete immutable record. Never truncate runners or features.
    compressed = gzip.compress(payload, compresslevel=6, mtime=0)
    if len(compressed) > 950000:
        raise ValueError("compressed D1 evidence exceeds endpoint limit")
    req = request.Request(endpoint, data=compressed, method="POST", headers={
        "Authorization": "Bearer " + secret,
        "Content-Type": "application/json",
        "Content-Encoding": "gzip",
    })
    sender = transport if transport is not None else request.urlopen
    try:
        response = sender(req, timeout=12)
        with response:
            status = response.status
            body = json.loads(response.read(5000).decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("D1 evidence transport or response failed") from exc
    if status not in (200, 201) or not isinstance(body, dict) or body.get("ok") is not True:
        raise ValueError("D1 evidence write rejected")
    if body.get("captureId") != capture_id or body.get("researchOnly") is not True:
        raise ValueError("D1 capture acknowledgement differs from local evidence")
    return {"captureId": capture_id, "remoteAccepted": True, "httpStatus": status,
            "researchOnly": True}
