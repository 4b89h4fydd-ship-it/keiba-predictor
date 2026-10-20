"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _parse_nar_live_odds_html(html: str) -> dict:
    return _parse_nar_odds_html(html, clean=_clean, parse_scratch_status=_scratch_status)

def _nar_live_odds(track:str,iso_date:str,race_no:int,force:bool=False)->dict:
    code=NAR_BABA_CODES.get(str(track or "").strip())
    if not code:return {}
    key=f"{code}|{iso_date}|{race_no}";now=time.time();ttl=int(os.getenv("NAR_LIVE_ODDS_CACHE_SEC","20"))
    with _nar_odds_cache_lock:
        hit=_nar_odds_cache.get(key)
        if hit and not force and now-hit[0]<ttl:return hit[1]

    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":iso_date.replace("-","/"),"k_raceNo":int(race_no),"t":int(time.time()*1000) if force else ""})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/OddsTanFuku_ipat?"+q,
    ]
    out={}
    for url in urls:
        req=urllib.request.Request(url,headers={
            "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
            "Accept-Language":"ja-JP,ja;q=0.9",
            "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
        })
        try:
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_ODDS_TIMEOUT_SEC","2.5"))) as res:
                html=_jra_decode(res.read())
            out=_parse_nar_live_odds_html(html)
            if out:break
        except Exception as exc:
            print("NAR odds fetch failed",track,iso_date,race_no,url,exc)

    with _nar_odds_cache_lock:
        _nar_odds_cache[key]=(now,out)
        if len(_nar_odds_cache)>64:
            oldest=min(_nar_odds_cache.items(),key=lambda kv:kv[1][0])[0];_nar_odds_cache.pop(oldest,None)
    return out

def _attach_nar_live_odds(detail:dict)->dict:
    if not detail:return detail
    odds=_nar_live_odds(str(detail.get("track") or ""),str(detail.get("date") or ""),int(detail.get("raceNumber") or 0))
    if not odds:return detail
    for h in detail.get("horses",[]) or []:
        z=odds.get(int(h.get("horseNumber") or 0))
        if z:
            delta=win_odds_delta(h.get("winOdds"),z.get("winOdds"))
            h.update({k:v for k,v in z.items() if v is not None and v!=""})
            if delta is not None: h["observedWinOddsDelta"]=delta
    detail["oddsSource"]="NAR公式"; detail["oddsType"]="単勝実オッズ"; detail["oddsUpdatedAt"]=odds_observed_at()
    return detail
