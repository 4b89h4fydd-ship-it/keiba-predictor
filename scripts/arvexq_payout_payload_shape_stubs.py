#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shape compact-tombstone entries in a result-repair payload.

The protect layer admits only a RESULT-ONLY write over a stored
nightly-compact tombstone stub: the incoming detail may differ from
the stored detail (as read through the API display view, which is
what protect compares against) in the result fields alone. A repair
payload built from the D1 bundle can diverge from that view in
volatile metadata (observed 2026-10-30 Kanazawa 01/08: oddsSource /
oddsUpdatedAt), which makes protect fail closed and blocks the whole
date's sync even though the stored race holds no forecast at all.

For every payload detail that is itself a compact tombstone stub,
this step fetches the API display detail (the same view protect
reads) and, when it is the same stub, rebuilds the entry as that
detail with only the result fields (result / resultCname / payouts)
taken from the repaired payload entry — a result-only write by
construction. Any fetch or shape problem leaves the entry untouched,
so protect keeps failing closed exactly as before.
"""
from __future__ import annotations

import argparse
import copy
import http.client
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.arvexq_protect_sync import _compact_tombstone_stub  # noqa: E402

_RESULT_KEYS = ("result", "resultCname", "payouts")


def fetch_display_detail(api_base: str, rid: str) -> dict[str, Any] | None:
    url = (api_base.rstrip("/") + "/api/race/"
           + urllib.parse.quote(rid, safe="")
           + "?view=display&sealguard=" + str(time.time_ns()))
    req = urllib.request.Request(
        url, headers={"accept": "application/json",
                      "user-agent": "ARVEXQ-SealGuard/1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read()
        except http.client.IncompleteRead as exc:
            # The API closes some responses without a clean chunked
            # terminator; the body bytes still arrived in full. The
            # JSON parse and identity checks below are the real gate.
            raw = exc.partial or b""
            if not raw:
                if attempt < 2:
                    time.sleep(2)
                continue
        except Exception:
            if attempt < 2:
                time.sleep(2)
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return None
        detail = data.get("detail") if isinstance(data, dict) else None
        return detail if isinstance(detail, dict) else None
    return None


def shape_payload(payload: dict[str, Any],
                  fetch: Callable[[str], dict[str, Any] | None]) -> list[str]:
    """Rebuild stub entries in place; return the race ids shaped."""
    shaped: list[str] = []
    for entry in payload.get("details") or []:
        if not isinstance(entry, dict) or not _compact_tombstone_stub(entry):
            continue
        rid = str(entry.get("id") or "")
        if not rid:
            continue
        stored = fetch(rid)
        if not isinstance(stored, dict) or str(stored.get("id") or "") != rid:
            print(f"SHAPE_SKIP {rid} (display detail unavailable)")
            continue
        if not _compact_tombstone_stub(stored):
            print(f"SHAPE_SKIP {rid} (display detail is not the stub)")
            continue
        rebuilt = copy.deepcopy(stored)
        for key in _RESULT_KEYS:
            if key in entry:
                rebuilt[key] = copy.deepcopy(entry[key])
        entry.clear()
        entry.update(rebuilt)
        shaped.append(rid)
    return shaped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    parser.add_argument(
        "--api-base",
        default=os.getenv("CLOUDFLARE_API_BASE",
                          "https://kraiz-api.4b89h4fydd.workers.dev"))
    args = parser.parse_args()

    path = Path(args.payload)
    payload = json.loads(path.read_text(encoding="utf-8"))
    shaped = shape_payload(
        payload, lambda rid: fetch_display_detail(args.api_base, rid))
    for rid in shaped:
        print(f"SHAPE_STUB {rid}")
    path.write_text(json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8")
    print(f"SHAPE_SUMMARY shaped={len(shaped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
