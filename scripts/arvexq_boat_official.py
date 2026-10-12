#!/usr/bin/env python3
"""BOATRACE official B (program) / K (results) -> a single verified daily record.

These are the official published downloads, NOT an extra racing provider.
Input uses boatrace-lzh's parser for LZH/Shift-JIS. No forecast or odds are invented.
Run only for personal research. Publishing outside a protected personal instance
is deliberately blocked by the existing commercial-rights publisher.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JST = timezone(timedelta(hours=9))
VENUE_NAMES = ("桐生","戸田","江戸川","平和島","多摩川","浜名湖","蒲郡","常滑","津","三国","びわこ",
               "住之江","尼崎","鳴門","丸亀","児島","宮島","徳山","下関","若松","芦屋","福岡","唐津","大村")
VENUE_BY_CODE = {f"{n:02d}": name for n,name in enumerate(VENUE_NAMES,1)}
SOURCE = "BOATRACE公式B/K"
MAX_DAILY_RACES = 24*12


def official_day_record(day: date, schedule: Any, close_times: list[Any],
                        performance: Any | None = None,
                        observed_at: datetime | None = None) -> dict[str, Any]:
    """Convert parser models into the app's existing date-scoped day contract.

    A race is admitted only with six distinct named official entries and an
    actual published closing time. Missing data is counted, never filled.
    """
    observed_at = observed_at or datetime.now(JST)
    if observed_at.tzinfo is None:
        raise ValueError("Observed timestamp must include timezone")
    stamp = observed_at.astimezone(JST).isoformat(timespec="seconds")
    iso = day.isoformat()
    times = {}
    for v in close_times:
        key=(str(getattr(v,"venue_code","")).zfill(2),getattr(v,"race_number",None))
        close=getattr(v,"close_time",None)
        if key in times or key[0] not in VENUE_BY_CODE or not isinstance(key[1],int):
            raise ValueError("Duplicate/invalid official closing time")
        if not isinstance(close,datetime) or close.tzinfo is None or close.date()!=day:
            raise ValueError("Official race closing time not verified")
        times[key]=v

    people = {int(p.racer_number):p for p in schedule.racers
              if getattr(p,"racer_number",None) and getattr(p,"name",None)}
    grouped = defaultdict(list)
    for entry in schedule.entries:
        key=(str(getattr(entry,"venue_code","")).zfill(2),getattr(entry,"race_number",None))
        grouped[key].append(entry)
    result_rows = defaultdict(list)
    pay_by_race=defaultdict(list)
    if performance:
        for row in performance.entries:
            key=(str(getattr(row,"venue_code","")).zfill(2),getattr(row,"race_number",None))
            result_rows[key].append(row)
        for p in performance.payouts:
            key=(str(getattr(p,"venue_code","")).zfill(2),getattr(p,"race_number",None))
            pay_by_race[key].append(p)
    races=[]
    dropped=[]
    known_keys=set()
    for raw in schedule.races:
        key=(str(getattr(raw,"venue_code","")).zfill(2),getattr(raw,"race_number",None))
        if key in known_keys:
            raise ValueError(f"Official race duplicate: {key}")
        known_keys.add(key)
        if key[0] not in VENUE_BY_CODE or not isinstance(key[1],int) or not 1<=key[1]<=12:
            dropped.append({"key":str(key),"reason":"invalid-race-identity"})
            continue
        reported_date=getattr(raw,"race_date",None)
        if reported_date and reported_date!=day:
            raise ValueError("Official B race date mismatch")
        close=times.get(key)
        if close is None:
            dropped.append({"key":str(key),"reason":"no-official-closing-time"})
            continue
        sources=grouped.get(key,[])
        nums=[getattr(e,"boat_number",None) for e in sources]
        if len(sources)!=6 or set(nums)!={1,2,3,4,5,6}:
            dropped.append({"key":str(key),"reason":"not-six-verified-boat-numbers"})
            continue
        entrants=[]
        for e in sorted(sources,key=lambda x:x.boat_number):
            racer=people.get(getattr(e,"racer_number",None))
            if racer is None or not str(racer.name).strip():
                break
            person={"racerNumber":racer.racer_number}
            for src,dest in (("racer_class","class"),("branch","branch"),("age","age"),("weight","weight")):
                v=getattr(racer,src,None)
                if v is not None:person[dest]=v
            ent={"boatNo":e.boat_number,"name":str(racer.name).strip(),"player":person}
            if getattr(e,"motor_number",None) is not None:
                ent["motor"]={"number":e.motor_number}
            if getattr(e,"boat_part",None) is not None:
                ent["boat"]={"number":e.boat_part}
            entrants.append(ent)
        if len(entrants)!=6:
            dropped.append({"key":str(key),"reason":"racer-name-not-verified"})
            continue

        t=close.close_time.astimezone(JST)
        venue=VENUE_BY_CODE[key[0]]
        record={
            "id":f"boat-{iso}-{venue}-{key[1]:02d}",
            "venue":venue,"venueCode":key[0],"raceNo":key[1],
            "title":str(getattr(close,"race_name",None) or getattr(raw,"race_name","") or ""),
            "closeAt":t.isoformat(timespec="seconds"),"closeTime":t.strftime("%H:%M"),
            "entries":entrants,"source":SOURCE,"sourceCheckedAt":stamp,
        }
        observations=result_rows.get(key,[])
        winning={int(x.result_position):int(x.boat_number) for x in observations
                 if getattr(x,"result_position",None) in (1,2,3)
                 and getattr(x,"boat_number",None) in (1,2,3,4,5,6)}
        exact=[p for p in pay_by_race.get(key,[]) if p.ticket_type=="sanrensho"]
        if len(winning)==3 and set(winning)=={1,2,3} and len(exact)==1:
            combo="-".join(str(winning[i]) for i in (1,2,3))
            paid=str(exact[0].winning_combination).replace(" ","").replace("－","-")
            if paid==combo and isinstance(exact[0].payout,int) and exact[0].payout>0:
                record["result"]={
                    "status":"confirmed","trifecta":combo,
                    "trifectaPayoutYen":exact[0].payout,
                    "confirmedAt":stamp,"timestampMeaning":"observed-from-official-K",
                    "finishers":[{"position":i,"boatNo":winning[i]} for i in (1,2,3)],
                }
            else:
                dropped.append({"key":str(key),"reason":"K-result-payout-inconsistent"})
        elif observations or exact:
            record["result"]={"status":"pending","sourceNote":"K-result-incomplete"}
        for row in observations:
            number=getattr(row,"boat_number",None)
            if number not in range(1,7):continue
            ent=entrants[number-1]
            if getattr(row,"exhibition_time",None) is not None:
                ent["exhibition"]={"time":row.exhibition_time}
            if getattr(row,"st_timing",None) is not None:
                ent["actualStartTiming"]=row.st_timing
        races.append(record)
    if len(races)>MAX_DAILY_RACES or len(races)!=len({r["id"] for r in races}):
        raise ValueError("Official daily race-count integrity failure")
    if not races:
        raise ValueError("No complete official B racecards; keep existing saved data")
    return {
        "version":"arvexq-boat-day-v1","date":iso,"verified":True,"verifiedAt":stamp,
        "dataStatus":"verified","provenanceId":"BOATRACE-OFFICIAL-BK-PERSONAL",
        "personalOnly":True,"races":sorted(races,key=lambda r:(r["venueCode"],r["raceNo"])),
        "dataAudit":{"source":SOURCE,"raceCount":len(races),"parsedRaceCount":len(known_keys),
                     "skipped":dropped,"hasOfficialK":bool(performance)},
    }


def acquire(day:date,cache_dir:Path)->dict[str,Any]:
    """One B download; optional one K download. No HTML scraping/extra providers."""
    try:
        from boatrace_lzh import LzhDownloader, ScheduleParser, PerformanceParser
    except ImportError as e:
        raise RuntimeError("Install reviewed boatrace-lzh==0.1.0 with p7zip-full") from e
    # No threaded/racing requests; prevent broad crawler spikes.
    d=LzhDownloader(cache_dir=cache_dir,request_delay=3.0,timeout=25,max_workers=1)
    b=d.download(day,"schedule")
    if not b:
        raise RuntimeError("Official B program missing or unavailable; no blank publish")
    sched=ScheduleParser()
    result=sched.parse(b)
    times=sched.parse_schedule_with_close_times(b,day)
    print("OFFICIAL_B_SOURCE_AUDIT", "archives=",len(b),
          "rawRaces=",len(result.races),"entries=",len(result.entries),
          "closingTimes=",len(times),
          "closeVenues=",sorted({str(t.venue_code) for t in times}),
          "parsedVenues=",sorted({str(r.venue_code) for r in result.races}))
    # K is posted after racing; one attempt, never infer missing results.
    k=d.download(day,"performance") if day<=datetime.now(JST).date() else {}
    perf=PerformanceParser().parse(k) if k else None
    print("OFFICIAL_K_SOURCE_AUDIT","archives=",len(k),
          "rawRaces=",len(perf.races) if perf else 0,
          "entries=",len(perf.entries) if perf else 0,
          "payouts=",len(perf.payouts) if perf else 0,
          "venues=",sorted({str(r.venue_code) for r in perf.races}) if perf else [])
    return official_day_record(day,result,times,perf)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--date",default=datetime.now(JST).strftime("%Y-%m-%d"))
    p.add_argument("--cache-dir",type=Path,default=Path(".cache/arvexq-boat-official"))
    p.add_argument("--output",type=Path,default=Path("data/private/boat-official"))
    p.add_argument("--publish",action="store_true",help="Only for an authenticated personal instance")
    a=p.parse_args()
    day=date.fromisoformat(a.date)
    data=acquire(day,a.cache_dir)
    a.output.mkdir(parents=True,exist_ok=True)
    target=a.output/(a.date+".json")
    tmp=target.with_suffix(".partial")
    tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    tmp.replace(target)
    print("OFFICIAL_BK_PERSONAL",a.date,"races=",len(data["races"]),"skipped=",len(data["dataAudit"]["skipped"]))
    if a.publish:
        # Publishing personal-only copies to a public workers.dev URL is NOT private.
        # Require explicit access review instead of silently distributing source data.
        if os.getenv("ARVEXQ_BOAT_PRIVATE_ACCESS_VERIFIED")!="1":
            raise SystemExit("BOAT_PUBLICATION_BLOCKED: set up and verify private access first")
        from scripts.arvexq_boat_ingest import ingest_personal_official
        published,_=ingest_personal_official(data,a.date)
        print("PERSONAL_OFFICIAL_PUBLISHED",published)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
