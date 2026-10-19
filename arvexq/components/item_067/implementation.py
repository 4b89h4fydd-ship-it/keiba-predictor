"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _restore_saved_odds(detail:dict)->dict:
    """Display-only odds must survive diagnosis/history/environment snapshot rebuilds."""
    if not isinstance(detail,dict):return detail
    race_id=str(detail.get("id") or "")
    if not race_id:return detail
    rows=[]
    try:rows=RACEDB.odds_latest(race_id) or []
    except Exception:rows=[]
    if not rows:
        try:
            previous,_=PREPARED_STORE.get(race_id)
            if previous:
                rows=[{
                    "horseNumber":h.get("horseNumber"),"winOdds":h.get("winOdds"),
                    "popularity":h.get("popularity"),"oddsSource":h.get("oddsSource") or previous.get("oddsSource")
                } for h in (previous.get("horses") or []) if not odds_missing(h)]
                if rows:
                    detail["oddsUpdatedAt"]=previous.get("oddsUpdatedAt") or detail.get("oddsUpdatedAt")
                    detail["oddsSource"]=previous.get("oddsSource") or detail.get("oddsSource")
        except Exception:pass
    if not rows:return detail
    by={int(h.get("horseNumber") or 0):h for h in (detail.get("horses") or [])}
    latest=0;source=""
    for z in rows:
        no=int(z.get("horseNumber") or 0);h=by.get(no)
        if not h:continue
        for k in ("winOdds","popularity"):
            if z.get(k) not in (None,""):h[k]=z.get(k)
        if z.get("oddsSource"):
            h["oddsSource"]=z.get("oddsSource");source=z.get("oddsSource")
        latest=max(latest,int(z.get("capturedAt") or 0))
    if source:detail["oddsSource"]=source
    if latest:
        detail["oddsUpdatedAt"]=datetime.fromtimestamp(latest,ZoneInfo("Asia/Tokyo")).strftime("%H:%M:%S")
    return detail
