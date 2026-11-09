"""Horse-level final results and live odds merges, with no application dependency."""
from datetime import datetime
from zoneinfo import ZoneInfo

def _merge_central_odds(detail:dict, odds:dict)->dict:
    if not odds:return detail
    by={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    for no,z in odds.items():
        h=by.get(int(no))
        if h:
            for k,v in z.items():
                if v not in (None,""):h[k]=v
    detail["oddsSource"]="netkeiba実オッズ";detail["oddsType"]="単勝実オッズ";detail["oddsUpdatedAt"]=datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%H:%M:%S")
    return detail

def _merge_result_fields(detail:dict,result:dict)->dict:
    fins=(result or {}).get("finishers") or []
    if not fins:return detail
    hs=detail.get("horses") if isinstance(detail.get("horses"),list) else []
    by={int(h.get("horseNumber") or 0):h for h in hs if int(h.get("horseNumber") or 0)>0}
    if not hs:
        hs=[];detail["horses"]=hs
    for f in fins:
        no=int(f.get("horseNumber") or 0)
        if not no:continue
        h=by.get(no)
        if h is None:
            h={"horseNumber":no,"frameNumber":int(f.get("frameNumber") or no),"name":str(f.get("name") or ""),"recentRaces":[],"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}}
            hs.append(h);by[no]=h
        for k in ("winOdds","popularity","bodyWeight","bodyWeightChange"):
            if f.get(k) not in (None,""):h[k]=f.get(k)
        if f.get("winOdds"):h["oddsSource"]="netkeiba最終"
        # The result parser is the only place this race's sectional facts
        # (last 3F above all) are observed. Write the finisher's own
        # performance back onto the horse record as its record of this race;
        # until now those values lived only in the race-level result block
        # and never reached any per-horse career record.
        performance={}
        for k in ("finish","timeSeconds","last3FSeconds","last3FRank","marginText","cornerPositions"):
            if f.get(k) not in (None,""):performance[k]=f.get(k)
        if performance:
            performance["date"]=detail.get("date") or ""
            performance["track"]=detail.get("track") or ""
            performance["raceNumber"]=int(detail.get("raceNumber") or 0)
            performance["source"]=(result or {}).get("source") or ""
            h["raceResult"]=performance
    if any(f.get("winOdds") for f in fins):
        detail["oddsSource"]="netkeiba最終";detail["oddsType"]="単勝最終オッズ";detail["oddsUpdatedAt"]=datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%H:%M:%S")
    detail["fieldSize"]=int(detail.get("fieldSize") or len(hs))
    return detail

