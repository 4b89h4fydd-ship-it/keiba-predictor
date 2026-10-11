"""supplemental/feeds: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.supplemental import _safe_int
from arvexq.ingest.parsers.supplemental import _smart_normalize_row
from arvexq.ingest.pure_parsers import _json_horse_rows
from arvexq.ingest.pure_parsers import _pick
from bs4 import BeautifulSoup
import html as html_lib
import json
import os
import re
import time
import urllib.parse
import urllib.request


from arvexq.ingest.supplemental.state import _smart_cache
from arvexq.ingest.supplemental.state import _smart_cache_lock

def _format_feed_url(base: str, detail: dict) -> str:
    vals={"date":str(detail.get("date") or ""),"yyyymmdd":str(detail.get("date") or "").replace("-",""),"track":str(detail.get("track") or ""),"race":str(detail.get("raceNumber") or ""),"circuit":str(detail.get("circuit") or ""),"race_id":str(detail.get("id") or "")}
    out=base; used=False
    for k,v in vals.items():
        token="{"+k+"}"
        if token in out:out=out.replace(token,urllib.parse.quote(v));used=True
    if not used:out+=("&" if "?" in out else "?")+urllib.parse.urlencode({"date":vals["date"],"track":vals["track"],"race":vals["race"],"circuit":vals["circuit"]})
    return out


def _fetch_json_url(url: str, timeout: float=4.0, token: str=''):
    headers={"User-Agent":"Mozilla/5.0 (compatible; KeibaPredictor/7.7)","Accept":"application/json,text/plain,*/*","Accept-Language":"ja-JP,ja;q=0.9"}
    if token:headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as res:return json.loads(res.read().decode("utf-8","ignore"))


def _extract_smartrc_embedded(html: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    for sc in soup.find_all("script"):
        raw=(sc.string or sc.get_text() or "").strip()
        if not raw or ("hname" not in raw and "horseNumber" not in raw and '"uno"' not in raw):continue
        candidates=[]
        if sc.get("type") in ("application/json","application/ld+json"):
            try:candidates.append(json.loads(raw))
            except Exception:pass
        for m in re.finditer(r"(?:=|:)\s*(\[[\s\S]{10,120000}?\]|\{[\s\S]{10,120000}?\})\s*;",raw):
            try:candidates.append(json.loads(html_lib.unescape(m.group(1))))
            except Exception:pass
        for c in candidates:
            rows=_json_horse_rows(c)
            if rows:return rows
    return []


def _fetch_smartrc(detail: dict, *, _fetch_json_url, _format_feed_url) -> dict:
    key=str(detail.get("id") or f"{detail.get('date')}|{detail.get('track')}|{detail.get('raceNumber')}");now=time.time()
    with _smart_cache_lock:
        hit=_smart_cache.get(key)
        if hit and now-hit[0]<600:return hit[1]
    feed=str(os.getenv("SMARTRC_FEED_URL","")).strip();token=str(os.getenv("SMARTRC_FEED_TOKEN","")).strip();out={"rows":[],"status":"browser","error":"","url":"https://www.smartrc.jp/v3/"}
    if feed:
        try:
            raw=_json_horse_rows(_fetch_json_url(_format_feed_url(feed,detail),float(os.getenv("SMARTRC_TIMEOUT_SEC","5")),token));rows=[z for z in (_smart_normalize_row(x) for x in raw) if z];out={"rows":rows,"status":"done" if rows else "unavailable","error":"","url":"https://www.smartrc.jp/v3/"}
        except Exception as exc:out={"rows":[],"status":"error","error":str(exc)[:220],"url":"https://www.smartrc.jp/v3/"}
    with _smart_cache_lock:_smart_cache[key]=(now,out)
    return out


def _fetch_extra_sources(detail: dict, *, _fetch_json_url, _format_feed_url) -> list[dict]:
    spec=str(os.getenv("EXTRA_RACE_FEEDS","")).strip(); out=[]
    if not spec:return out
    for part in spec.split(";"):
        part=part.strip()
        if not part:continue
        name,url=(part.split("=",1) if "=" in part else ("補助",part))
        try:
            body=_fetch_json_url(_format_feed_url(url.strip(),detail),float(os.getenv("EXTRA_FEED_TIMEOUT_SEC","4")),str(os.getenv("EXTRA_FEED_TOKEN","")).strip()); rows=[]
            for x in _json_horse_rows(body):
                no=_safe_int(_pick(x,"horseNumber","horse_no","uno","number","馬番"));hn=str(_pick(x,"name","hname","horseName","馬名") or "").strip()
                if no or hn:rows.append({"horseNumber":no,"name":hn,"extra":x})
            if rows:out.append({"source":name.strip() or "補助","rows":rows})
        except Exception as exc:print("extra source failed",name,exc)
    return out
