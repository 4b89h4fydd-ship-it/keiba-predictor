#!/usr/bin/env python3
"""Read-only nightly audit: every race vs a genuine pre-off sealed prediction.

Cannot forge missing archives; records exactly which races failed to preserve
a pre-race opinion and whether an archived ticket was captured or unavailable.
"""
from __future__ import annotations
import argparse
import json
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from arvexq.prediction.prerace_archive import JST, post_at, sealed_lock
from scripts.arvexq_fetch_d1_bundle import get_json, detail_from_response


def inspect(row: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    rid = str(row.get("id") or "")
    status = str(row.get("raceStatus") or row.get("status") or "")
    skipped = any(word in status for word in ("取止", "中止", "取り止め", "不成立"))
    if skipped:
        return {"race_id": rid, "status": "race-cancelled", "reason": status}
    if not isinstance(detail, dict):
        return {"race_id": rid, "status": "missing-race-detail"}
    seal = sealed_lock(detail)
    if seal is None:
        return {"race_id": rid, "status": "missing-preoff-seal"}
    bet = detail.get("preRaceBet")
    if not isinstance(bet, dict) or not bet.get("fixedAt"):
        ticket = "missing"
    elif bet.get("captureStatus") == "failed" or bet.get("decision") == "未取得":
        ticket = "capture-failed"
    else:
        ticket = "recorded"
    return {
        "race_id": rid, "status": "sealed", "ticket": ticket,
        "revision": seal.get("sealRevision") or seal.get("revision") or "",
        "captured_at_epoch": seal.get("capturedAtEpoch"),
        "race_date": detail.get("date"),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-base", default=os.getenv("CLOUDFLARE_API_BASE", "https://kraiz-api.4b89h4fydd.workers.dev"))
    p.add_argument("--date", default="")
    p.add_argument("--report", default="arvexq-daily-archive-audit.json")
    p.add_argument("--workers", type=int, default=3)
    args = p.parse_args()
    day = args.date or (datetime.now(JST).date()-timedelta(days=1)).isoformat()
    base = args.api_base.rstrip("/")
    url = base + "/api/day?date=" + urllib.parse.quote(day) + "&details=0"
    day_data = get_json(url,timeout=30,retries=6)
    races = [r for r in (day_data.get("races") or []) if isinstance(r,dict) and r.get("id")]
    reports: dict[str, dict[str, Any]] = {}
    def fetch(row: dict[str, Any]) -> dict[str, Any]:
        rid = str(row["id"])
        try:
            fetched = get_json(base + "/api/race/" + urllib.parse.quote(rid,safe=""),
                               timeout=30,retries=6)
            return inspect(row,detail_from_response(fetched,rid))
        except Exception as exc:
            return {"race_id": rid, "status": "verification-read-error",
                    "reason": f"{type(exc).__name__}: {exc}"[:320]}
    if races:
        with ThreadPoolExecutor(max_workers=max(1,min(args.workers,4,len(races)))) as ex:
            futs={ex.submit(fetch,row):str(row["id"]) for row in races}
            for fut in as_completed(futs):
                reports[futs[fut]]=fut.result()
    ordered=[reports[str(r["id"])] for r in races]
    sealed=[r for r in ordered if r["status"]=="sealed"]
    cancelled=[r for r in ordered if r["status"]=="race-cancelled"]
    missing=[r for r in ordered if r["status"] not in ("sealed","race-cancelled")]
    tickets_missing=[r for r in sealed if r.get("ticket")!="recorded"]
    report={
        "version":"arvexq-full-day-prerace-archive-audit-v1", "date":day,
        "race_count":len(races), "sealed_count":len(sealed), "cancelled_count":len(cancelled),
        "unsealed_count":len(missing),"ticket_missing_count":len(tickets_missing),
        "archive_complete":bool(races) and not missing and not tickets_missing,
        "unsealed_races":missing,"missing_tickets":tickets_missing,"all_races":ordered,
    }
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("ARVEXQ_NIGHTLY_PRERACE_AUDIT",json.dumps({k:report[k] for k in
          ("date","race_count","sealed_count","cancelled_count",
           "unsealed_count","ticket_missing_count","archive_complete")},ensure_ascii=False))
    for row in (missing+tickets_missing)[:30]:
        print("ARCHIVE_MISSING",row)
    # Absence of a day is a legitimate non-racing day; fail only when known
    # scheduled races lack provenance. Do not backfill a historical prediction.
    return 2 if missing or tickets_missing else 0


if __name__=="__main__":
    raise SystemExit(main())
