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
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from arvexq.prediction.prerace_archive import pre_off, restore_seal, sealed_lock


def fetch_current(base: str, rid: str) -> dict[str, Any] | None:
    url = base.rstrip("/") + "/api/race/" + urllib.parse.quote(rid, safe="") + "?sealguard=" + str(time.time_ns())
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": "ARVEXQ-SealGuard/1"})
    # Worker/D1 503s are sometimes transient. Retry boundedly, but never
    # treat a failed read as 'no previous archive' (that would allow erasure).
    failure = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # No D1 race detail is expected at the start of a new day.
                # Require an independently successful date-scoped day response;
                # do not convert arbitrary 404s (bad routes/outages) to absence.
                match = re.search(r"20\d{2}-\d{2}-\d{2}", rid)
                if not match:
                    raise RuntimeError("D1 seal-guard cannot verify 404 without race date") from exc
                date = match.group(0)
                day_url = base.rstrip("/") + "/api/day?date=" + urllib.parse.quote(date) + "&details=0"
                try:
                    day_req = urllib.request.Request(
                        day_url, headers={"accept": "application/json", "user-agent": "ARVEXQ-SealGuard/1"}
                    )
                    with urllib.request.urlopen(day_req, timeout=25) as response:
                        day = json.loads(response.read().decode("utf-8"))
                    if not isinstance(day, dict) or not isinstance(day.get("races"), list):
                        raise ValueError("unverifiable D1 day response")
                    if day.get("date") and str(day["date"]) != date:
                        raise ValueError("D1 day date mismatch")
                except Exception as day_exc:
                    raise RuntimeError("D1 seal-guard 404 cannot be confirmed as a missing race") from day_exc
                return None
            failure = exc
        except Exception as exc:
            failure = exc
        if attempt == 4:
            raise RuntimeError("D1 seal-guard lookup failed closed: "+str(failure)) from failure
        time.sleep(min(5.0, 0.6*(2**attempt)))
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


def verify_published(body: dict[str, Any], *, base: str, read=fetch_current) -> list[str]:
    """Detect a concurrent D1 sync that removed or rewrote a pre-race seal.

    This is not a substitute for an atomic Worker-side compare-and-swap,
    but it makes lost archives observable rather than silently claiming success.
    """
    verified: list[str] = []
    for detail in body.get("details") or []:
        if not isinstance(detail, dict) or not detail.get("id"):
            continue
        lock = sealed_lock(detail)
        if not lock:
            continue
        rid = str(detail["id"])
        actual = read(base, rid)
        current = sealed_lock(actual or {})
        if not current or current != lock:
            raise RuntimeError("D1_SEAL_POST_VERIFY_MISMATCH " + rid)
        bet = detail.get("preRaceBet")
        if isinstance(bet, dict) and (actual or {}).get("preRaceBet") != bet:
            raise RuntimeError("D1_PRE_RACE_BET_POST_VERIFY_MISMATCH " + rid)
        verified.append(rid)
    return verified


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--verify-post", action="store_true")
    p.add_argument("--api-base", default=os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev"))
    args=p.parse_args()
    path=Path(args.file)
    body=json.loads(path.read_text(encoding="utf-8"))
    if args.verify_post:
        verified = verify_published(body, base=args.api_base)
        print("D1_SEAL_POST_VERIFY_OK", len(verified), ",".join(verified[:10]))
        return 0
    changed=guard(body, base=args.api_base)
    # Atomic rewrite: never send a partially guarded batch.
    tmp=path.with_name(path.name+".sealed.tmp")
    tmp.write_text(json.dumps(changed,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    tmp.replace(path)
    print("D1_SEAL_GUARD",path.name,"details",len(changed.get("details") or []))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
