#!/usr/bin/env python3
"""Single audited boat data publisher for a commercial-use-authorized normalized feed.

Input is an acquired, rights-attested and verified JSON day snapshot.
This tool DOES NOT scrape BOATRACE or infer races/payouts/odds.
Usage: python scripts/arvexq_boat_publish.py licensed_day.json
"""
from __future__ import annotations
import argparse
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VENUES=("桐生","戸田","江戸川","平和島","多摩川","浜名湖","蒲郡","常滑","津","三国","びわこ",
        "住之江","尼崎","鳴門","丸亀","児島","宮島","徳山","下関","若松","芦屋","福岡","唐津","大村")
RESULT_STATUSES={"confirmed","pending","cancelled","速報"}
URL_SCHEMA="arvexq-boat-day-v1"


def timepoint(text: str) -> datetime:
    dt=datetime.fromisoformat(str(text).replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timezone must be explicit")
    return dt


def validate_day(obj: dict) -> dict:
    if not isinstance(obj,dict) or obj.get("version")!=URL_SCHEMA or obj.get("verified") is not True:
        raise ValueError("Expected verified date-scoped ARVEXQ source")
    day=obj.get("date")
    if not isinstance(day,str) or not re.fullmatch(r"\d{4}-\d\d-\d\d",day):
        raise ValueError("Invalid race date")
    datetime.strptime(day,"%Y-%m-%d")
    rights=obj.get("rights") or {}
    if rights.get("commercialUseAuthorized") is not True or not rights.get("provenanceId") or not rights.get("permissionEvidence"):
        raise ValueError("Licensed commercial feed with documented permission is required")
    if not obj.get("verifiedAt"):
        raise ValueError("Verified snapshot needs timestamp")
    timepoint(obj["verifiedAt"])
    races=obj.get("races")
    if not isinstance(races,list) or not races:
        raise ValueError("At least one verified race is needed; no fabricated venue data")
    seen=set()
    for r in races:
        if not isinstance(r,dict) or r.get("venue") not in VENUES or type(r.get("raceNo")) is not int or not 1<=r["raceNo"]<=12:
            raise ValueError("Invalid venue or race number")
        expected="boat-"+day+"-"+r["venue"]+"-"+str(r["raceNo"]).zfill(2)
        if r.get("id")!=expected or expected in seen:
            raise ValueError("Invalid or duplicate race identity")
        seen.add(expected)
        close=timepoint(r["closeAt"])
        if not r.get("closeTime"):
            raise ValueError("Scheduled cutoff time missing")
        entries=r.get("entries")
        if entries is not None and entries!=[]:
            if len(entries)!=6 or {e.get("boatNo") for e in entries}!={1,2,3,4,5,6} or any(not str(e.get("name","")).strip() for e in entries):
                raise ValueError("Invalid 6-boat program")
        f=r.get("forecast")
        if f:
            if not entries or len(entries)!=6 or f.get("status")!="verified":
                raise ValueError("Predictions must be verified and based on 6 starters")
            if timepoint(f["snapshotAt"])>=close:
                raise ValueError("After-start predictions are never publishable")
            tickets=f.get("tickets",[])
            if not 1<=len(tickets)<=6:
                raise ValueError("Only 1-6 trifecta combinations")
            codes=[]
            for ticket in tickets:
                code=ticket if isinstance(ticket,str) else ticket.get("combination")
                if not isinstance(code,str) or not re.fullmatch(r"[1-6]-[1-6]-[1-6]",code) or len(set(code.split("-")))!=3:
                    raise ValueError("Invalid ticket")
                codes.append(code)
            if len(set(codes))!=len(codes):
                raise ValueError("Duplicate tickets")
            # AI probabilities remain experimental until a full chronological
            # calibration receipt is attached and independently validated.
            if f.get("model",{}).get("experimental") is True:
                raise ValueError("Experimental model is not publishable as verified")
        result=r.get("result")
        if result and result.get("status") not in RESULT_STATUSES:
            raise ValueError("Unknown result status")
        if result and result.get("status")=="confirmed":
            t=result.get("trifecta")
            if not isinstance(t,str) or not re.fullmatch(r"[1-6]-[1-6]-[1-6]",t) or len(set(t.split("-")))!=3:
                raise ValueError("Confirmed result lacks official trifecta")
            if not result.get("confirmedAt"):
                raise ValueError("Confirmed timestamp missing")
        odds=r.get("odds3t")
        if odds:
            if odds.get("verified") is not True or odds.get("source") not in ("BOATRACE公式","正規許諾フィード"):
                raise ValueError("Unverified odds source")
            timepoint(odds["updatedAt"])
            for code,val in odds.get("values",{}).items():
                if not re.fullmatch(r"[1-6]-[1-6]-[1-6]",str(code)) or len(set(code.split("-")))!=3 or isinstance(val,bool) or not isinstance(val,(int,float)) or not 1<=val<=100000:
                    raise ValueError("Odds must be sourced numeric 3連単")
    # Public payload only includes information useful to the racing client;
    # remove internal permission evidence and contacts.
    return {"version":URL_SCHEMA,"date":day,"verified":True,
            "verifiedAt":obj["verifiedAt"],"races":races,
            "dataStatus":"verified","provenanceId":rights["provenanceId"]}


def publish(input_path: Path,output_dir: Path) -> Path:
    data=json.loads(input_path.read_text(encoding="utf-8"))
    safe=validate_day(data)
    output_dir.mkdir(parents=True,exist_ok=True)
    target=output_dir/(safe["date"]+".json")
    fd,temp=tempfile.mkstemp(dir=output_dir,prefix=".boat-",suffix=".tmp")
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as fp:
            json.dump(safe,fp,ensure_ascii=False,separators=(",",":"),allow_nan=False)
            fp.write("\n")
        os.replace(temp,target)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return target

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,default=ROOT/"arvexq/ui/static/sports/boat-data")
    args=parser.parse_args()
    print("BOAT_PUBLISH_VERIFIED",publish(args.input,args.output))

if __name__=="__main__":main()
