"""Parse netkeiba win odds payload without application or HTTP dependencies."""
import json
import re

def _parse_netkeiba_win_odds_payload(raw:str)->dict:
    if not raw:return {}
    s=str(raw).strip()
    if not s.startswith("{"):
        m=re.search(r"\((\{.*\})\)\s*;?\s*$",s,re.S)
        if m:s=m.group(1)
    try:body=json.loads(s)
    except Exception:return {}
    data=body.get("data") if isinstance(body,dict) else None
    odds=(data.get("odds") if isinstance(data,dict) else None) or {}
    win=odds.get("1") if isinstance(odds,dict) else None
    if win is None and isinstance(odds,dict):win=odds.get(1)
    if not isinstance(win,dict):return {}
    out={}
    for k,v in win.items():
        try:no=int(str(k))
        except Exception:continue
        odd=None;pop=None
        if isinstance(v,(list,tuple)):
            if len(v)>0:
                candidate=str(v[0]).replace(",","").strip()
                if re.fullmatch(r"\d+(?:\.\d+)?",candidate):
                    try:odd=float(candidate)
                    except Exception:odd=None
            if len(v)>2:
                try:pop=int(float(v[2]))
                except Exception:pop=None
        elif isinstance(v,dict):
            for kk in ("odds","win","tan"):
                if v.get(kk) not in (None,""):
                    try:odd=float(v.get(kk));break
                    except Exception:pass
            for kk in ("popularity","popular","rank","ninki"):
                if v.get(kk) not in (None,""):
                    try:pop=int(float(v.get(kk)));break
                    except Exception:pass
        if odd is not None and odd>0:
            out[no]={"winOdds":odd,"popularity":pop,"oddsSource":"netkeiba実オッズ"}
    return out


def _parse_netkeiba_place_odds_payload(raw:str)->dict:
    """Place （複勝） ranges from the same netkeiba JRA odds payload.

    Mirrors _parse_netkeiba_win_odds_payload's shape: the type=1 payload
    carries bet types under data.odds, "1" for win and "2" for place. A
    place entry is a range, read positionally as [low, high, popularity]
    for list entries (a single value means low == high) or from explicit
    low/high keys for dict entries. Anything that does not parse as an
    ordered positive range is dropped: no range is ever derived from the
    win odds. (Live shape verification against a real weekend payload is
    still outstanding; an unexpected shape simply yields {}.)
    """
    if not raw:return {}
    s=str(raw).strip()
    if not s.startswith("{"):
        m=re.search(r"\((\{.*\})\)\s*;?\s*$",s,re.S)
        if m:s=m.group(1)
    try:body=json.loads(s)
    except Exception:return {}
    data=body.get("data") if isinstance(body,dict) else None
    odds=(data.get("odds") if isinstance(data,dict) else None) or {}
    place=odds.get("2") if isinstance(odds,dict) else None
    if place is None and isinstance(odds,dict):place=odds.get(2)
    if not isinstance(place,dict):return {}

    def _num(value):
        try:
            f=float(str(value).replace(",","").strip())
        except Exception:
            return None
        return f if f>0 else None

    out={}
    for k,v in place.items():
        try:no=int(str(k))
        except Exception:continue
        low=None;high=None
        if isinstance(v,(list,tuple)):
            if len(v)>0:low=_num(v[0])
            if len(v)>1:high=_num(v[1])
            if high is None:high=low
        elif isinstance(v,dict):
            for kk in ("low","min","placeOddsLow","from"):
                if v.get(kk) not in (None,""):
                    low=_num(v.get(kk))
                    if low is not None:break
            for kk in ("high","max","placeOddsHigh","to"):
                if v.get(kk) not in (None,""):
                    high=_num(v.get(kk))
                    if high is not None:break
            if high is None:high=low
            if low is None:low=high
        if low is not None and high is not None and high>=low:
            out[no]={"placeOddsLow":low,"placeOddsHigh":high}
    return out


