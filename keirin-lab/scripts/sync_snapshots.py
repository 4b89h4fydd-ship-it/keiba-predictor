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

def predict(entries):
    riders=[]
    for e in entries:
        try:
            n=int(e["umaban"]); score=float(e["score"])
            win=float(e["win_rate"])/100; place=float(e["top3_rate"])/100
        except (KeyError,TypeError,ValueError):
            return None
        if not 0<=win<=place<=1:
            return None
        riders.append({"n":n,"score":score,"win":win,"place":place,"style":e.get("style","")})
    if len(riders)<3 or len(set(x["n"] for x in riders))!=len(riders):
        return None
    import math
    mean=sum(x["score"] for x in riders)/len(riders)
    for x in riders:
        x["w"]=math.exp(max(-9,min(9,(x["score"]-mean)/8+1.1*(x["win"]-.15)+.5*(x["place"]-.4)+(.08 if x["style"]=="逃" else 0))))
    total=sum(x["w"] for x in riders)
    output=[]
    for a in riders:
        for b in riders:
            for c in riders:
                if len({a["n"],b["n"],c["n"]})!=3: continue
                p=a["w"]/total*b["w"]/(total-a["w"])*c["w"]/(total-a["w"]-b["w"])
                output.append({"ticket":f'{a["n"]}-{b["n"]}-{c["n"]}',"p":round(p,9)})
    output.sort(key=lambda x:x["p"],reverse=True)
    bynum={x["n"]:{"number":x["n"],"p1":0,"p3":0} for x in riders}
    for x in output:
        a,b,c=map(int,x["ticket"].split("-"))
        bynum[a]["p1"]+=x["p"]
        for n in (a,b,c): bynum[n]["p3"]+=x["p"]
    rank=sorted(bynum.values(),key=lambda x:x["p1"],reverse=True)
    return {"model":"keirin-score-heuristic-v1-uncalibrated","marks":dict(zip(["◎","○","▲","△","☆"],[x["number"] for x in rank[:5]])), "riders":rank,"trifecta":output[:20]}

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
                    prediction=predict(race["entries"])
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
