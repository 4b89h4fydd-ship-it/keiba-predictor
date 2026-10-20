"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _merge_live_market_rows(race_id:str, fresh_rows:list[dict], saved:dict|None=None)->list[dict]:
    """Preserve the best known live fields per horse when a source returns a partial table.

    A live odds page can briefly omit one or more runners while updating.  Never let
    that sparse response erase previously captured odds/body weight for other horses.
    Fresh non-empty fields win; the latest RaceDB point and saved race snapshot fill gaps.
    """
    by_no:dict[int,dict]={}
    saved=saved or {}
    for h in (saved.get("horses") or []):
        try:no=int(h.get("horseNumber") or 0)
        except Exception:no=0
        if not no:continue
        z={"horseNumber":no}
        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange","oddsForecast",
                  "referenceBodyWeight","referenceBodyWeightDate","status","scratched","oddsSource"):
            if h.get(k) not in (None,""):z[k]=h.get(k)
        by_no[no]=z
    try:
        for h in RACEDB.odds_latest(race_id) or []:
            no=int(h.get("horseNumber") or 0)
            if not no:continue
            z=by_no.setdefault(no,{"horseNumber":no})
            for k in ("winOdds","popularity","oddsSource"):
                if z.get(k) in (None,"") and h.get(k) not in (None,""):z[k]=h.get(k)
    except Exception as exc:
        print("odds preserve read failed",race_id,exc)
    for h in fresh_rows or []:
        try:no=int(h.get("horseNumber") or 0)
        except Exception:no=0
        if not no:continue
        z=by_no.setdefault(no,{"horseNumber":no})
        fresh_odds=h.get("winOdds")
        if fresh_odds not in (None,"") and str(fresh_odds)!=str(z.get("winOdds") or ""):
            # An older stored popularity must not be attached to a newly
            # published price when the upstream row has no current rank.
            z.pop("popularity",None)
        for k,v in h.items():
            if k=="horseNumber":continue
            if v not in (None,""):z[k]=v
    return [by_no[k] for k in sorted(by_no)]
