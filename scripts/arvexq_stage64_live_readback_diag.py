"""Read-only diagnosis of the EXISTING ARVEXQ production D1 detail path.

No fetching from alternative providers, no model modifications, no D1 writes.
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from arvexq.forecast.engine import _preoff, build_prediction
from arvexq.research.stage64.pipeline import predict

RACES = (
    "nar-2026-10-23-園田-09",
    "nar-2026-10-23-園田-11",
    "nar-2026-10-23-浦和-11",
    "nar-2026-10-23-笠松-11",
)
API = "https://kraiz-api.4b89h4fydd.workers.dev/api/race/"

for race_id in RACES:
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    try:
        with urllib.request.urlopen(
            urllib.request.Request(API + urllib.parse.quote(race_id, safe=""),
                headers={"Accept": "application/json", "User-Agent": "ARVEXQ-D1-Hydrator/1"}),
            timeout=15
        ) as response:
            obj = json.load(response)
        d = obj["detail"]
        horses = d.get("horses") or []
        observations = []
        for h in horses:
            runs = h.get("recentRaces") or []
            viable = sum(type(x.get("fieldSize")) is int and type(x.get("finish")) in (int, float) for x in runs)
            corners = sum(bool(x.get("cornerPositions") or x.get("passing")) for x in runs)
            observations.append([h.get("horseNumber"), len(runs), viable, corners])
        output = {"id":race_id, "nowJST":now.isoformat(timespec="seconds"),
                  "off":d.get("startTime"), "preoff":_preoff(d, now),
                  "state":d.get("predictionStatus"), "model":d.get("predictionModelVersion"),
                  "roster":len(horses), "observations":observations}
        if _preoff(d, now):
            raw=dict(d)
            raw["circuit"]="nar"
            try:
                shadow=predict(raw,expected_circuit="nar")
                output["stage64Blockers"]=shadow.get("blockers")
                output["stageStatuses"]={k:v.get("status") for k,v in shadow.get("stages",{}).items()}
            except Exception as e:
                output["stage64Error"]=type(e).__name__+":"+str(e)[:150]
            try:
                official=build_prediction(d,now=now)
                output["approvedAdapterReady"]=bool(official)
            except Exception as e:
                output["adapterError"]=type(e).__name__+":"+str(e)[:150]
        print("ARVEXQ_LIVE_STAGE64_D1_DIAGNOSTIC", json.dumps(output,ensure_ascii=False,separators=(",",":")),flush=True)
    except Exception as e:
        print("ARVEXQ_LIVE_STAGE64_D1_ERROR",race_id,type(e).__name__,str(e)[:180],flush=True)
