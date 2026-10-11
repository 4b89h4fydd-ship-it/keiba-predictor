"""central/jra/transport: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.pure_parsers import _jra_decode
import os
import time
import urllib.parse
import urllib.request


from arvexq.ingest.central.jra.state import _jra_cache_lock
from arvexq.ingest.central.jra.state import _jra_text_cache

def _jra_request(url: str, cname: str | None=None, cache_sec: int=1800) -> str:
    key=url+"|"+(cname or "")
    now=time.time()
    with _jra_cache_lock:
        hit=_jra_text_cache.get(key)
        if hit and now-hit[0] < cache_sec:
            return hit[1]
    headers={"User-Agent":"Mozilla/5.0 (compatible; KeibaPredictor/6.2; +https://www.jra.go.jp/)","Accept-Language":"ja,en;q=0.8"}
    data=None
    if cname:
        data=urllib.parse.urlencode({"cname":cname}).encode("ascii")
        headers["Content-Type"]="application/x-www-form-urlencoded"
    req=urllib.request.Request(url,data=data,headers=headers)
    with urllib.request.urlopen(req,timeout=float(os.getenv("JRA_OFFICIAL_TIMEOUT_SEC","4.5"))) as res:
        text=_jra_decode(res.read())
    with _jra_cache_lock:
        _jra_text_cache[key]=(now,text)
    return text
