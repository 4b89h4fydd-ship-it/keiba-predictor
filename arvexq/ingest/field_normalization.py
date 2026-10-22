"""Pure field normalization for JRA/NAR ingestion; no UI or predictions."""
from __future__ import annotations
import re
from arvexq.components.item_036.runner_cancellation import extract as cancellation_status
from arvexq.components.item_037.runner_exclusion import extract as exclusion_status

def _clean(value: str | None) -> str:
    return (value or "").strip().replace("\u3000", " ")

def _int(value: str | None, default: int = 0) -> int:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default

def _float(value: str | None, default: float = 0.0) -> float:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default

def _carried_weight(value: str | None, default: float = 0.0) -> float:
    s = _clean(value).replace(",", "")
    if not s:
        return default
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return default
    try:
        return float(m.group(0))
    except ValueError:
        return default

def _iso_date(yyyymmdd: str) -> str:
    s = re.sub(r"\D", "", yyyymmdd)
    if len(s) != 8:
        return yyyymmdd
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"

def _start_time(hhmm: str) -> str:
    s = re.sub(r"\D", "", hhmm)
    if len(s) == 3:
        s = "0" + s
    if len(s) != 4:
        return _clean(hhmm)
    return f"{s[:2]}:{s[2:]}"

def _time_seconds(raw: str) -> float:
    s = re.sub(r"[^0-9]", "", _clean(raw))
    if not s:
        return 0.0
    if len(s) <= 3:
        return int(s) / 10.0
    return int(s[:-3]) * 60 + int(s[-3:]) / 10.0

def _normalize_sex(value: str) -> str:
    from arvexq.components.item_028.sex import normalize
    return normalize(value)

def _scratch_status(value: str) -> str:
    s = _clean(value)
    if not s:
        return ""
    return exclusion_status(s) or cancellation_status(s)

def _normalize_weather(value: str) -> str:
    s = _clean(value)
    for v in ("晴", "曇", "小雨", "雨", "小雪", "雪"):
        if v in s:
            return v
    return "不明"

def _normalize_condition(value: str) -> str:
    s = _clean(value)
    for v in ("不良", "稍重", "重", "良"):
        if v in s:
            return v
    return "不明"
