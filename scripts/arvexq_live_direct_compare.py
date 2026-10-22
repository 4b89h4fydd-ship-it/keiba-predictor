#!/usr/bin/env python3
"""Read-only live API pre-off prediction/result comparison; no local or MotherDuck race store.

Existing API day summaries enumerate races. The existing race detail endpoint
provides an original frozen forecast and the result, and both are compared by
race ID. Missing pre-off prediction is an explicit unscorable state.
"""
from __future__ import annotations
import argparse
import json
import sys
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from arvexq.prediction.prerace_archive import sealed_lock, JST
from scripts.arvexq_fetch_d1_bundle import get_json, detail_from_response

API="https://kraiz-api.4b89h4fydd.workers.dev"

def evaluate(detail):
    lock=sealed_lock(detail)
    if lock is None:return "no_verified_preoff_forecast",None
    finishers=((detail.get("result") or {}).get("finishers") or [])
    winners=[int(f.get("horseNumber")) for f in finishers if isinstance(f,dict)
             and str(f.get("finish") or "")=="1" and str(f.get("horseNumber") or "").isdigit()]
    if len(winners)!=1:return "no_unique_confirmed_winner",None
    try: pick=int(lock.get("winnerNo") or lock.get("honmeiHorseNumber") or 0)
    except (ValueError,TypeError):pick=0
    if not pick:return "no_preoff_winner_pick",None
    return "evaluated",int(pick==winners[0])

def scan_day(day,base=API):
    base=base.rstrip("/")
    daily=get_json(base+"/api/day?"+urllib.parse.urlencode({"date":day,"details":0}),30,3)
    if not isinstance(daily.get("races"),list):raise ValueError("missing race list")
    count=Counter(); wins=0
    ids=[str(row["id"]) for row in daily["races"] if isinstance(row,dict) and row.get("id")]
    def fetch_one(rid):
        try:
            raw=get_json(base+"/api/race/"+urllib.parse.quote(rid,safe=""),30,3)
            detail=detail_from_response(raw,rid)
            if detail is None:raise ValueError("race detail mismatch")
            return evaluate(detail)
        except Exception:
            return "read_error",None
    with ThreadPoolExecutor(max_workers=6) as pool:
        for status,hit in pool.map(fetch_one,ids):
            count[status]+=1
            if hit is not None:wins+=hit
    return {"date":day,"races":sum(count.values()),"status":dict(count),"wins":wins}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--days",type=int,default=7)
    args=p.parse_args()
    if not 1<=args.days<=14:p.error("--days must be 1..14")
    today=datetime.now(JST).date()
    rows=[]
    for delta in range(1,args.days+1):
        day=(today-timedelta(days=delta)).isoformat()
        try:
            report=scan_day(day)
            rows.append(report)
            print("LIVE_DAY_COMPARE",json.dumps(report,ensure_ascii=False))
        except Exception as exc:
            rows.append({"date":day,"error_type":type(exc).__name__})
            print("LIVE_DAY_READ_ERROR",day,type(exc).__name__)
    evaluated=sum(r.get("status",{}).get("evaluated",0) for r in rows)
    wins=sum(r.get("wins",0) for r in rows)
    missing=sum(r.get("status",{}).get("no_verified_preoff_forecast",0) for r in rows)
    errors=sum(r.get("status",{}).get("read_error",0) for r in rows)
    print("LIVE_DIRECT_COMPARISON",json.dumps({"days":args.days,"evaluated":evaluated,"winner_hits":wins,"hit_rate":round(wins/evaluated,4) if evaluated else None,"missing_preoff_forecast":missing,"detail_read_errors":errors,"day_errors":sum("error_type" in r for r in rows),"saved_race_dataset_required":False,"writes":0},ensure_ascii=False))
    if not evaluated or errors or any("error_type" in r for r in rows):raise SystemExit(2)

if __name__=="__main__":main()
