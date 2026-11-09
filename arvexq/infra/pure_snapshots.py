"""Pure, standalone race snapshot utilities.

Moved verbatim from app.py; the corresponding app-level names remain imported.
No external API, DB, or live racing access is performed at import time.
"""

def _bundle_quality(p:dict|None)->tuple:
    p=p or {}
    return (
        int(p.get("raceCount") or 0),
        int(p.get("detailCount") or 0),
        int(p.get("generatedAtEpoch") or p.get("updatedAtEpoch") or 0),
        int(p.get("analysisCount") or 0),
    )


def _racedb_snapshot_usable(detail:dict)->bool:
    if not isinstance(detail,dict):return False
    horses=detail.get("horses")
    if not isinstance(horses,list) or not horses:return False
    return all(isinstance(h,dict) and h.get("name") and int(h.get("horseNumber") or 0)>0 for h in horses)


def _merge_official_result(detail:dict,official:dict)->dict:
    if not official:return detail
    # Identity guard: an official block that names a different race
    # (its date / track / race number disagree with the detail's) is
    # never merged. A wrong-race result token once overwrote a race's
    # title, distance, field size and finish order wholesale, and the
    # merged block then read as final so nothing re-checked it
    # (2026-11-08 Fukushima 7R carried Hanshin 2026-09-20 8R's result).
    for key in ("date","track","raceNumber"):
        mine=detail.get(key); theirs=official.get(key)
        if mine not in (None,"",0) and theirs not in (None,"",0) and str(mine)!=str(theirs):
            return detail
    for k in ("title","distance","surface","condition","weather","racePrize1","startTime","scheduledStartTime","resultCname"):
        v=official.get(k)
        if v not in (None,"",0,"不明"):detail[k]=v
    if official.get("result"):detail["result"]=official["result"]
    by_no={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    for f in (official.get("result") or {}).get("finishers",[]) or []:
        no=int(f.get("horseNumber") or 0);h=by_no.get(no)
        if not h:
            h={"horseNumber":no,"frameNumber":f.get("frameNumber") or no,"name":f.get("name") or "","sex":f.get("sex") or "","age":f.get("age") or 0,"carriedWeight":f.get("carriedWeight") or 0,"jockey":f.get("jockey") or "","trainer":f.get("trainer") or "","recentRaces":[],"jockeyStats":{},"trainerStats":{},"jockeyProfile":{},"trainerProfile":{}}
            detail.setdefault("horses",[]).append(h);by_no[no]=h
        for k in ("frameNumber","name","sex","age","carriedWeight","jockey","trainer","bodyWeight","bodyWeightChange"):
            if f.get(k) not in (None,"",0):h[k]=f.get(k)
    # Field size never shrinks at merge time: the official parse
    # derives it from the finisher rows it happened to read, so a
    # partial (interim) table would otherwise overwrite the card's
    # full field with its own row count (2026-11-08 Fukushima 9R:
    # fieldSize 16 overwritten by a 5-row interim parse).
    finishers=(official.get("result") or {}).get("finishers") or []
    detail["fieldSize"]=max(int(detail.get("fieldSize") or 0),
                            len(detail.get("horses",[]) or []),
                            len(finishers));return detail
