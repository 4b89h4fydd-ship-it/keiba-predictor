"""Independent horse-body and carried-weight validation for race ingestion."""
from __future__ import annotations
import re

def _safe_body_weight_value(value):
    if value in (None,""):return None
    try:
        m=re.search(r"(?<!\d)(\d{3})(?!\d)",str(value))
        x=int(m.group(1)) if m else int(round(float(value)))
    except Exception:return None
    return x if 250<=x<=800 else None


def _safe_carried_weight_value(value, body_weight=None):
    if value in (None,""):return None
    try:x=float(re.sub(r"[^0-9.+-]","",str(value)))
    except Exception:return None
    # Strict mode: 斤量 is already a kg value. Do not auto-divide 3-digit values,
    # because a horse body weight such as 500 can otherwise become a false 50kg.
    if 35<=x<=80:return round(x,1)
    return None


def _sanitize_horse_measurements(h:dict)->dict:
    if not isinstance(h,dict):return h
    z=dict(h)
    bw=_safe_body_weight_value(z.get("bodyWeight") or z.get("horseWeight") or z.get("currentBodyWeight"))
    z["bodyWeight"]=bw
    ch=z.get("bodyWeightChange")
    try:ch=int(float(ch)) if ch not in (None,"") else None
    except Exception:ch=None
    z["bodyWeightChange"]=ch if ch is not None and abs(ch)<=99 else None
    z["carriedWeight"]=_safe_carried_weight_value(z.get("carriedWeight"),bw)
    runs=[]
    for rr in list(z.get("allPastRuns") or z.get("recentRaces") or []):
        if not isinstance(rr,dict):continue
        q=dict(rr);rbw=_safe_body_weight_value(q.get("bodyWeight"));q["bodyWeight"]=rbw
        q["carriedWeight"]=_safe_carried_weight_value(q.get("carriedWeight"),rbw)
        runs.append(q)
    if z.get("allPastRuns") is not None:z["allPastRuns"]=runs
    z["recentRaces"]=runs[:5]
    return z


