#!/usr/bin/env python3
"""Read-only Cloudflare D1 storage audit. Never makes write/delete requests."""
from __future__ import annotations
import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

CF_API = "https://api.cloudflare.com/client/v4"
FREE_DB_LIMIT = 500_000_000
PAID_DB_LIMIT = 10_000_000_000


def get_cloudflare_json(path: str, token: str, *, opener=urllib.request.urlopen) -> dict[str, Any]:
    if not path.startswith("/accounts/") or "/d1/database" not in path:
        raise ValueError("only D1 read endpoints are allowed")
    req = urllib.request.Request(CF_API + path,
                                 headers={"Authorization": "Bearer " + token,
                                          "accept": "application/json",
                                          "User-Agent": "ARVEXQ-D1-Storage-Audit/1"},
                                 method="GET")
    with opener(req, timeout=20) as response:
        value = json.loads(response.read(1_000_000).decode("utf-8"))
    if not isinstance(value, dict) or value.get("success") is not True:
        raise RuntimeError("Cloudflare D1 read request failed")
    return value


def summarize(databases: list[dict[str, Any]], *, plan: str = "unknown") -> dict[str, Any]:
    if plan not in ("free", "paid", "unknown"):
        raise ValueError("plan must be free, paid or unknown")
    entries = []
    total = 0
    for row in databases:
        size = row.get("file_size")
        if not isinstance(size, (float, int)) or size < 0:
            raise ValueError("D1 database size missing or invalid; no invented estimate")
        size = int(size)
        total += size
        entries.append({
            "name": row.get("name") or "unidentified",
            "uuid": row.get("uuid") or "",
            "bytes": size, "mb": round(size / 1_000_000, 2),
            "free_usage_pct": round(size / FREE_DB_LIMIT * 100, 2),
            "paid_usage_pct": round(size / PAID_DB_LIMIT * 100, 2),
        })
    chosen = FREE_DB_LIMIT if plan == "free" else PAID_DB_LIMIT if plan == "paid" else None
    return {"version": "arvexq-readonly-d1-storage-v1",
            "plan": plan, "writes_performed": 0,
            "database_count": len(entries),
            "account_observed_bytes": total,
            "per_database_limit_bytes": chosen,
            "warning_at_percent": 85,
            "critical_at_percent": 95,
            "critical": any(item["bytes"] >= chosen * .95 for item in entries) if chosen else None,
            "warning": any(item["bytes"] >= chosen * .85 for item in entries) if chosen else None,
            "databases": sorted(entries, key=lambda x:x["bytes"], reverse=True)}


def audit(account: str, token: str, *, database_name: str = "",
          plan: str = "unknown", get=get_cloudflare_json) -> dict[str, Any]:
    if not account or not token:
        raise RuntimeError("Cloudflare account ID or read token unavailable")
    results = get("/accounts/" + urllib.parse.quote(account, safe="") + "/d1/database?per_page=100", token)
    matches = results.get("result")
    if not isinstance(matches, list):
        raise RuntimeError("Cloudflare D1 database listing unavailable")
    rows = []
    for item in matches:
        if not isinstance(item, dict) or not item.get("uuid"):
            continue
        if database_name and str(item.get("name") or "").lower() != database_name.lower():
            continue
        details = get("/accounts/" + urllib.parse.quote(account, safe="") +
                      "/d1/database/" + urllib.parse.quote(str(item["uuid"]), safe=""), token).get("result")
        if not isinstance(details, dict):
            raise RuntimeError("D1 database metrics unavailable; no zero-size fallback")
        rows.append(details)
    if database_name and not rows:
        raise RuntimeError("Requested D1 database not found or not accessible")
    if not rows:
        raise RuntimeError("No readable D1 databases")
    return summarize(rows, plan=plan)


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--out", default="")
    p.add_argument("--plan", choices=("free","paid","unknown"),
                   default=os.getenv("ARVEXQ_CLOUDFLARE_WORKERS_PLAN", "unknown").lower())
    p.add_argument("--database", default=os.getenv("ARVEXQ_D1_DATABASE_NAME",""))
    args=p.parse_args()
    try:
        report=audit(os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
                     os.environ.get("CLOUDFLARE_API_TOKEN", ""),
                     database_name=args.database,plan=args.plan)
    except Exception as exc:
        # Never echo token or a network exception carrying request headers.
        print("D1_STORAGE_AUDIT_UNAVAILABLE", type(exc).__name__,
              "data_preserved=true", "no_mutation=true")
        return 2
    for row in report["databases"]:
        print("D1_STORAGE", row["name"], "mb="+str(row["mb"]),
              "free_pct="+str(row["free_usage_pct"]),
              "paid_pct="+str(row["paid_usage_pct"]))
    print("D1_STORAGE_AUDIT", "plan="+report["plan"],
          "critical="+str(report["critical"]),
          "database_count="+str(report["database_count"]),
          "data_preserved=true")
    if args.out:
        Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
