"""netkeiba/transport: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.pure_parsers import _decode_site
import time
import urllib.parse
import urllib.request


from arvexq.ingest.netkeiba.state import _netkeiba_cache
from arvexq.ingest.netkeiba.state import _netkeiba_cache_lock

def _netkeiba_get(url: str, timeout: float=4.0, cache_sec: int=45) -> str:
    now=time.time()
    with _netkeiba_cache_lock:
        hit=_netkeiba_cache.get(url)
        if hit and now-hit[0]<cache_sec:return hit[1]
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1","Referer":"https://race.netkeiba.com/","Accept-Language":"ja-JP,ja;q=0.9"})
    with urllib.request.urlopen(req,timeout=timeout) as res: txt=_decode_site(res.read())
    with _netkeiba_cache_lock:
        _netkeiba_cache[url]=(now,txt)
        if len(_netkeiba_cache)>80:
            k=min(_netkeiba_cache.items(),key=lambda kv:kv[1][0])[0];_netkeiba_cache.pop(k,None)
    return txt
