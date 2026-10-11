"""environment/transport: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.pure_parsers import _jra_decode
import os
import time
import urllib.parse
import urllib.request


from arvexq.ingest.environment.state import _environment_http_cache
from arvexq.ingest.environment.state import _environment_http_lock

def _environment_http_get(url: str, ttl: int=30) -> str:
    now=time.time()
    with _environment_http_lock:
        hit=_environment_http_cache.get(url)
        if hit and now-hit[0]<ttl:return str(hit[1].get("html") or "")
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
        "Accept-Language":"ja-JP,ja;q=0.9",
    })
    with urllib.request.urlopen(req,timeout=float(os.getenv("RACE_ENV_TIMEOUT_SEC","2.8"))) as res:
        html=_jra_decode(res.read())
    with _environment_http_lock:
        _environment_http_cache[url]=(now,{"html":html})
        if len(_environment_http_cache)>80:
            oldest=min(_environment_http_cache.items(),key=lambda kv:kv[1][0])[0]
            _environment_http_cache.pop(oldest,None)
    return html
