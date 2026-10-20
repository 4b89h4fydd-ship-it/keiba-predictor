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


