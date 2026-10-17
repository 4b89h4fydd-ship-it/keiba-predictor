"""Pure weather, condition, and third-party number parsing."""
from __future__ import annotations
import re
from arvexq.ingest.field_normalization import _clean

def _env_clean_weather(v:str)->str:
    s=_clean(v)
    for x in ("小雨","小雪","晴","曇","雨","雪"):
        if x in s:return x
    return "不明"

def _env_clean_condition(v:str)->str:
    s=_clean(v)
    for x in ("不良","稍重","重","良"):
        if x in s:return x
    return "不明"

def _safe_float(v):
    try:
        if v is None or v=="": return None
        if isinstance(v,str):
            m=re.search(r"-?\d+(?:\.\d+)?",v.replace(",","").strip())
            if not m:return None
            v=m.group(0)
        return float(v)
    except Exception:return None

def _safe_int(v):
    x=_safe_float(v); return int(x) if x is not None else None

