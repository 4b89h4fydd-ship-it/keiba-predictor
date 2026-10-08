#!/usr/bin/env python3
"""Protect existing server-authoritative pre-off forecasts in each D1 sync batch.

Run immediately before a Worker /api/sync write. Missing remote state is not
assumed empty: fail closed when a lookup fails, rather than erase an archive.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from arvexq.prediction.prerace_archive import pre_off, restore_seal, sealed_lock


def fetch_current(base: str, rid: str) -> dict[str, Any] | None:
    url = base.rstrip("/") + "/api/race/" + urllib.parse.quote(rid, safe="") + "?sealguard=" + str(time.time_ns())
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "ARVEXQ-SealGuard/1"})
    with urllib.request.urlopen(req, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("invalid D1 response")
    for item in (data.get("detail"), data.get("race"), data):
        if isinstance(item, dict) and str(item.get("id") or "") == rid:
            return item
    if data.get("ok") is False:
        raise RuntimeError("D1 returned failure")
    # The provider explicitly reports no detail; no historical snapshot to merge.
    if not data.get("detail") and not data.get("race") and not data.get("id"):
        return None
    raise RuntimeError("D1 returned a mismatched race")


def protect_detail(old: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(incoming)
    if not isinstance(old, dict):
        return out
    if sealed_lock(old):
        return restore_seal(old, out)
    prior = old.get("preRacePrediction")
    if isinstance(prior, dict) and pre_off(prior, old):
        incoming_lock = out.get("preRacePrediction")
        # Protect the first genuinely pre-off archived opinion after post.
        # A later, unverified "forecast" must never overwrite the prior record.
        from arvexq.prediction.prerace_archive import post_at, JST
        from datetime import datetime
        start = post_at(old)
        if start and datetime.now(JST) >= start:
            out["preRacePrediction"] = copy.deepcopy(prior)
        elif not isinstance(incoming_lock, dict):
            out["preRacePrediction"] = copy.deepcopy(prior)
    return out


def guard(body: dict[str, Any], read=fetch_current, *, base: str) -> dict[str, Any]:
    out = copy.deepcopy(body)
    updated = []
    for detail in out.get("details") or []:
        if not isinstance(detail, dict) or not detail.get("id"):
            continue
        old = read(base, str(detail["id"]))
        updated.append(protect_detail(old, detail))
    if out.get("details") is not None:
        out["details"] = updated
    return out


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--api-base", default=os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev"))
    args=p.parse_args()
    path=Path(args.file)
    body=json.loads(path.read_text(encoding="utf-8"))
    changed=guard(body, base=args.api_base)
    # Atomic rewrite: never send a partially guarded batch.
    tmp=path.with_name(path.name+".sealed.tmp")
    tmp.write_text(json.dumps(changed,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    tmp.replace(path)
    print("D1_SEAL_GUARD",path.name,"details",len(changed.get("details") or []))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
