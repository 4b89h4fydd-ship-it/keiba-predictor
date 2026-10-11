"""netkeiba/odds: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.parsers.market import _parse_netkeiba_win_odds_payload
import os
import time
import urllib.parse
import urllib.request


def _netkeiba_live_win_odds(detail: dict, force: bool=False, *, _netkeiba_get, _netkeiba_race_id) -> dict:
    rid=str(detail.get("netkeibaRaceId") or "") or _netkeiba_race_id(
        str(detail.get("date") or ""),str(detail.get("track") or ""),int(detail.get("raceNumber") or 0)
    )
    if not rid:return {}
    base="https://race.netkeiba.com/api/api_get_jra_odds.html"
    nonce=f"&t={int(time.time()*1000)}" if force else ""
    common=f"pid=api_get_jra_odds&race_id={urllib.parse.quote(rid)}&type=1&sort=odds&compress=0&output=json"
    urls=[f"{base}?{common}&action=update{nonce}",f"{base}?{common}&action=init{nonce}"]
    for url in urls:
        try:
            raw=_netkeiba_get(url,float(os.getenv("NETKEIBA_ODDS_TIMEOUT_SEC","3.0")),
                              0 if force else int(os.getenv("NETKEIBA_ODDS_CACHE_SEC","8")))
            out=_parse_netkeiba_win_odds_payload(raw)
            if out:return out
        except Exception as exc:
            print("netkeiba odds api failed",rid,exc)
    return {}
