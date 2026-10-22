#!/usr/bin/env python3
"""ARVEXQ: isolated, opt-in analytics copy from existing read-only day API to MotherDuck.
Default is dry-run: NO SQL writes. Never changes Cloudflare D1 or production app.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import urllib.request
import urllib.error
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

JST=timezone(timedelta(hours=9))
BASE=os.environ.get("ARVEXQ_API_URL","https://kraiz-api.4b89h4fydd.workers.dev").rstrip("/")

def fetch_day(day: str) -> list[dict]:
    url=BASE+"/api/day?"+urlencode({"date":day,"details":"1"})
    req=urllib.request.Request(url,headers={"User-Agent":"ARVEXQ-Analytics-ReadOnly/1.0","Accept":"application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=75) as res:
                obj=json.loads(res.read(25_000_000))
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2:
                raise
            time.sleep(1.5 * (attempt+1))
    if not isinstance(obj,dict) or not isinstance(obj.get("details"),list):
        raise RuntimeError("day API schema invalid")
    return [d for d in obj["details"] if isinstance(d,dict)]

def normalize(rows: list[dict], day: str) -> list[tuple]:
    out={}
    for d in rows:
        race_id=str(d.get("id") or "")
        if not race_id or len(race_id)>180:
            continue
        raw=json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        digest=hashlib.sha256(raw.encode("utf-8")).hexdigest()
        out[race_id]=(race_id,day,digest,raw)
    return list(out.values())

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--days",type=int,default=1)
    p.add_argument("--apply",action="store_true",help="Opt-in MotherDuck analytics writes only")
    args=p.parse_args()
    if not 1<=args.days<=7:
        p.error("days must be 1..7")
    today=datetime.now(JST).date()
    rows=[]
    failed_days=[]
    for offset in range(1,args.days+1):
        day=(today-timedelta(days=offset)).isoformat()
        try:
            subset=normalize(fetch_day(day),day)
        except urllib.error.HTTPError as exc:
            failed_days.append(day)
            print("SOURCE_DAY_UNAVAILABLE",day,"http_status="+str(exc.code))
            continue
        print("SOURCE_DAY",day,"races",len(subset))
        rows.extend(subset)
    if failed_days:
        print("ANALYTICS_MISSING_DAYS",",".join(failed_days))
    if not rows:
        raise RuntimeError("No source days available; refusing sync")
    if not args.apply:
        print("ANALYTICS_DRY_RUN_OK", "races="+str(len(rows)), "missing_days="+str(len(failed_days)), "source_writes=0", "destination_writes=0")
        return
    if not os.environ.get("motherduck_token"):
        raise RuntimeError("motherduck_token missing")
    import duckdb
    db=duckdb.connect("md:my_db")
    try:
        db.execute("CREATE SCHEMA IF NOT EXISTS arvexq_analytics")
        db.execute("""CREATE TABLE IF NOT EXISTS arvexq_analytics.race_snapshots (
          race_id VARCHAR PRIMARY KEY, race_date DATE NOT NULL,
          sha256 VARCHAR NOT NULL, snapshot_json JSON NOT NULL,
          ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Transactional upsert; no changes to the application's D1.
        db.execute("BEGIN TRANSACTION")
        try:
            for id,day,digest,raw in rows:
                db.execute("""INSERT INTO arvexq_analytics.race_snapshots
                  (race_id,race_date,sha256,snapshot_json)
                  VALUES (?,CAST(? AS DATE),?,?)
                  ON CONFLICT(race_id) DO UPDATE SET
                  race_date=excluded.race_date,sha256=excluded.sha256,
                  snapshot_json=excluded.snapshot_json,
                  ingested_at=now()
                  WHERE arvexq_analytics.race_snapshots.sha256 IS DISTINCT FROM excluded.sha256
                """,[id,day,digest,raw])
            for rid,day,digest,raw in rows:
                observed=db.execute("SELECT sha256 FROM arvexq_analytics.race_snapshots WHERE race_id=?",[rid]).fetchone()
                if observed is None or observed[0] != digest:
                    raise RuntimeError("analytics readback mismatch")
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        print("ANALYTICS_MOTHERDUCK_SYNC_OK","verified_races="+str(len(rows)),"missing_days="+str(len(failed_days)),"cloudflare_writes=0")
    finally:
        db.close()

if __name__=="__main__":
    main()
