"""Extracted legacy behavior; network and stores stay outside this module."""
from __future__ import annotations

import re
from datetime import date as dt_date, datetime
from typing import Iterator


def iter_months_back(target: dt_date, count: int) -> Iterator[tuple[int, int]]:
    year, month = target.year, target.month
    for _ in range(count):
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        yield year, month


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


def _months_from_race_date(iso_date: str, count: int):
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    y, m = d.year, d.month
    for _ in range(max(1, count)):
        yield y, m
        m -= 1
        if m == 0:
            y -= 1
            m = 12


def _race_minutes_server(row:dict)->int:
    m=re.match(r"^(\d{1,2}):(\d{2})",str(row.get("startTime") or row.get("scheduledStartTime") or ""))
    return int(m.group(1))*60+int(m.group(2)) if m else 9999

