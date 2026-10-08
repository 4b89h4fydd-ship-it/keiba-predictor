"""Guard official course-state changes before revising a fixed morning mark.

Official going/cushion/moisture is observed information, not an official
forecast of front-runners, rail advantage or finishing order. Only trusted
source-identified records can request a bounded pre-off revision.
"""
from __future__ import annotations
from datetime import datetime
from urllib.parse import urlparse
from typing import Any

from arvexq.prediction.prerace_archive import JST, post_at

HOSTS = {"jra.go.jp", "www.jra.go.jp", "jra.jp", "www.jra.jp",
         "nar.netkeiba.com"}  # Do NOT trust aggregators as official feeds.
NAR_HOSTS = {"www.keiba.go.jp", "keiba.go.jp", "www.nankankeiba.com",
             "www.tokyocitykeiba.com", "www.sonoda-himeji.jp",
             "www.kanazawakeiba.com", "www.nagoyakeiba.com",
             "www.kasamatsu-keiba.com", "www.iwatekeiba.or.jp",
             "www.sagakeiba.net", "www.keiba.or.jp",
             "www.urawa-keiba.jp", "www.kawasaki-keiba.jp",
             "www.funabashi-keiba.net"}
HOSTS = (HOSTS - {"nar.netkeiba.com"}) | NAR_HOSTS
GOING = {"良", "稍重", "重", "不良"}


def official_event(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or value.get("sourceKind") != "official_course_condition":
        return None
    address = str(value.get("sourceUrl") or "")
    url = urlparse(address)
    if url.scheme != "https" or (url.hostname or "").lower() not in HOSTS:
        return None
    published = str(value.get("publishedAt") or "")
    try:
        instant = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            return None
    except (ValueError, TypeError):
        return None
    going = str(value.get("going") or "").replace("稍重", "稍重")
    if going not in GOING:
        return None
    surface = str(value.get("surface") or "")
    if surface not in {"芝", "ダート", "障害", "turf", "dirt", "jump"}:
        return None
    normalized = {"sourceKind": "official_course_condition",
                  "sourceUrl": address, "publishedAt":instant.isoformat(),
                  "going":going, "surface":surface}
    for field, low, high in (("cushionValue",3,18),
                             ("moisturePercent",0,50)):
        raw = value.get(field)
        if raw is None or raw == "":
            continue
        try:
            number = float(raw)
            if not low <= number <= high:
                return None
            normalized[field] = round(number, 2)
        except (ValueError,TypeError):
            return None
    return normalized


def meaningful_change(old: Any, new: Any, *, now: datetime) -> str:
    """Return a narrow, auditable reason; no change from weather or race results."""
    latest = official_event(new)
    if not latest:
        return ""
    stamp = datetime.fromisoformat(latest["publishedAt"])
    if stamp > now.astimezone(stamp.tzinfo):
        return ""
    previous = official_event(old)
    if previous:
        before = datetime.fromisoformat(previous["publishedAt"])
        if stamp <= before or latest["surface"] != previous["surface"]:
            return ""
        if latest["going"] != previous["going"]:
            return "公式馬場状態変更 "+previous["going"]+"→"+latest["going"]
        for key, unit, limit in (("cushionValue","クッション値",.5),
                                 ("moisturePercent","含水率",2.0)):
            if key in latest and key in previous and abs(latest[key]-previous[key]) >= limit:
                return "公式"+unit+"の有意な変動"
        return ""
    # First official publication is the only allowed initial measurement revision.
    return "公式馬場情報の初回発表"


def pre_off_change(detail: dict[str, Any], old: Any, new: Any, now: datetime) -> str:
    post = post_at(detail)
    if not post or now.astimezone(JST) >= post:
        return ""
    return meaningful_change(old, new, now=now)
