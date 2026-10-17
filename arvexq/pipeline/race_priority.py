"""Independent, deterministic race priority ordering for the collector."""
from __future__ import annotations
import re

def _race_minutes(row:dict)->int:
    s=str(row.get("startTime") or "")
    m=re.match(r"^(\d{1,2}):(\d{2})$",s)
    return int(m.group(1))*60+int(m.group(2)) if m else 9999

def _commercial_target_rows(rows:list[dict], now_min:int)->list[dict]:
    """Commercial mode prepares the whole day; upcoming races are simply first."""
    valid=[r for r in rows if r.get("id") and r.get("track")]
    valid.sort(key=lambda r:(
        0 if _race_minutes(r)>=now_min-25 else 1,
        abs(_race_minutes(r)-now_min),
        str(r.get("track") or ""),
        int(r.get("raceNumber") or 0),
    ))
    seen=set();out=[]
    for r in valid:
        rid=str(r.get("id") or "")
        if rid and rid not in seen:
            seen.add(rid);out.append(r)
    return out


