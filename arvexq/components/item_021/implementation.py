"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _parse_nar_official_card_html(detail:dict, html:str)->list[dict]:
    return _parse_nar_official_card(detail, html, _clean)

def _nar_official_card_rows_fast(detail:dict)->list[dict]:
    """Fetch NAR official current body weight/change from multiple official card layouts."""
    code=NAR_BABA_CODES.get(str(detail.get("track") or ""))
    if not code:return []
    date=str(detail.get("date") or "")
    race_no=int(detail.get("raceNumber") or 0)
    if not date or not race_no:return []
    q=urllib.parse.urlencode({
        "k_babaCode":code,
        "k_raceDate":date.replace("-","/"),
        "k_raceNo":race_no,
    })
    # DebaTableSmall exposes 馬体重 / 変更 as simple columns and is the most
    # reliable source for the current value. Keep the other official layouts as fallbacks.
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTableSmall?"+q,
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTable?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/DebaTable_ipat?"+q,
        "https://www.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_DebaTable?"+q,
        "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_DebaTable?"+q,
    ]
    out_by_no={}
    # Every active runner matters. Do not stop at N-1 coverage: that caused the
    # last horse on some NAR cards to remain "未発表" even after the official
    # card had published its body weight.
    target=max(1,len([h for h in detail.get("horses",[]) or [] if not h.get("scratched")]))
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja-JP,ja;q=0.9",
                "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_CARD_TIMEOUT_SEC","4.0"))) as res:
                html=_jra_decode(res.read())
        except Exception as exc:
            print("NAR official card failed",detail.get("id"),url,exc);continue
        for row in _parse_nar_official_card_html(detail,html):
            no=int(row.get("horseNumber") or 0)
            if no:out_by_no[no]=row
        if out_by_no and (not target or len(out_by_no)>=target):break
    return [out_by_no[k] for k in sorted(out_by_no)]

def _nar_official_result_fast(detail:dict)->dict|None:
    """Fetch NAR official RaceMarkTable directly; includes result, body weight and corner order."""
    code=NAR_BABA_CODES.get(str(detail.get("track") or "").strip())
    date=str(detail.get("date") or "")
    race_no=int(detail.get("raceNumber") or 0)
    if not code or not date or not race_no:return None
    q=urllib.parse.urlencode({"k_babaCode":code,"k_raceDate":date.replace("-","/"),"k_raceNo":race_no})
    urls=[
        "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?"+q,
        "https://www.keiba.go.jp/KeibaWeb_IPAT/TodayRaceInfo/RaceMarkTable_ipat?"+q,
    ]
    known={_clean(h.get("name")):int(h.get("horseNumber") or 0) for h in detail.get("horses",[]) or [] if h.get("name")}
    last_err=""
    source_reasons=[]
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja-JP,ja;q=0.9",
                "Referer":"https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_RESULT_TIMEOUT_SEC","4.0"))) as res:
                html=_jra_decode(res.read())
        except Exception as exc:
            last_err=str(exc)
            source_reasons.append("fetch_error:"+type(exc).__name__)
            continue
        if not html:
            source_reasons.append("empty_html")
            continue
        out = _parse_nar_result_html(
            html, known=known, clean=_clean, parse_payouts=_parse_payouts,
            clean_weather=_env_clean_weather, clean_condition=_env_clean_condition)
        if out is None:
            source_reasons.append("result_table_unrecognized_or_incomplete")
            continue
        out["sourceUrl"]=url
        return out
    print("NAR_RESULT_UNRESOLVED",detail.get("id"),"reasons="+",".join(source_reasons or ["not_parsed"]),
          "last_fetch_error="+last_err[:100] if last_err else "")
    return None
