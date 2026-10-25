#!/usr/bin/env python3
"""KEIRIN LAB snapshot sync. Never update a confirmed prediction."""
import datetime as dt
import json
import os
import pathlib
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1] / "public" / "snapshots"
JST = ZoneInfo("Asia/Tokyo")
SOURCE = "https://raw.githubusercontent.com/snarfnet/keirin-data/main/entries_{}.json"

def pull(day):
    url = SOURCE.format(day.strftime("%Y%m%d"))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"KEIRIN-LAB-Snapshot/1.0"}), timeout=20) as r:
            data=json.load(r)
    except Exception as exc:
        print("NO_SOURCE", day.isoformat(), type(exc).__name__)
        return None
    return data if isinstance(data.get("races"), list) else None

from engine import predict

def main():
    now=dt.datetime.now(JST)
    ROOT.mkdir(parents=True,exist_ok=True)
    changed=0
    for date in (now.date(),now.date()+dt.timedelta(days=1)):
        source=pull(date)
        if not source: continue
        path=ROOT/(date.isoformat()+".json")
        existing=json.loads(path.read_text()) if path.exists() else {"date":date.isoformat(),"races":{}}
        items=existing.setdefault("races",{})
        for race in source["races"]:
            rid=str(race.get("race_id",""))
            if not rid: continue
            old=items.get(rid,{})
            record=dict(old)
            record["race_id"]=rid
            record["venue"]=race.get("venue","")
            record["race_no"]=race.get("race_no")
            record["start_time"]=race.get("start_time")
            record["entries"]=race.get("entries",[]) # latest card separate from frozen prediction
            if "prediction" not in old and isinstance(race.get("entries"),list):
                hour=race.get("start_time")
                try:
                    scheduled=dt.datetime.combine(date,dt.time.fromisoformat(hour),JST)
                except (TypeError,ValueError):
                    scheduled=None
                # Freeze before departure only, never on historical/late input.
                if scheduled and now<scheduled:
                    prediction=predict(race)
                    if prediction:
                        record["prediction"]=prediction
                        record["prediction_confirmed_at"]=now.isoformat()
                        record["prediction_snapshot_id"]=rid+"-"+now.strftime("%Y%m%d%H%M%S")
            result=race.get("result_top3")
            if isinstance(result,list) and len(result)==3 and all(isinstance(v,int) for v in result):
                record["result_top3"]=result
                if isinstance(race.get("payout_trifecta"),(int,float)):
                    record["payout_trifecta"]=race["payout_trifecta"]
            items[rid]=record
        content=json.dumps(existing,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n"
        if not path.exists() or path.read_text()!=content:
            path.write_text(content)
            changed+=1
    print("CHANGED_DAYS",changed)

if __name__=="__main__": main()
