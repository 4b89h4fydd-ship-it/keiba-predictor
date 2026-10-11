"""merge/current: acquisition behavior preserved from PR #13 (95f2595).

Keyword-only ports are supplied by the application composition root.
This module never imports app or initializes storage/background workers.
"""
from arvexq.ingest.history.run_merge import _jra_merge_runs


def _merge_central_odds(detail: dict, odds: dict, *, _now_jst) -> dict:
    if not odds:return detail
    by={int(h.get("horseNumber") or 0):h for h in detail.get("horses",[]) or []}
    for no,z in odds.items():
        h=by.get(int(no))
        if h:
            for k,v in z.items():
                if v not in (None,""):h[k]=v
    detail["oddsSource"]="netkeiba実オッズ";detail["oddsType"]="単勝実オッズ";detail["oddsUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    return detail


def _merge_result_fields(detail: dict, result: dict, *, _now_jst) -> dict:
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
    if any(f.get("winOdds") for f in fins):
        detail["oddsSource"]="netkeiba最終";detail["oddsType"]="単勝最終オッズ";detail["oddsUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    detail["fieldSize"]=int(detail.get("fieldSize") or len(hs))
    return detail


def _merge_enrichment(detail: dict, data: dict, *, _strip_excluded) -> dict:
    hs=detail.get("horses") or [];by_no={int(h.get("horseNumber") or 0):h for h in hs if h.get("horseNumber")};by_name={str(h.get("name") or "").strip():h for h in hs if h.get("name")};sources=[]
    for row in data.get("smartRows") or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
        if not h:continue
        if "SmartRc" not in sources:sources.append("SmartRc")
        if row.get("smartRc"):h["smartRc"]={**(h.get("smartRc") or {}),**row.get("smartRc")}
        if row.get("pedigree"):h["pedigree"]={**(h.get("pedigree") or {}),**row.get("pedigree")}
        for k in ("owner","producer","birthday"):
            if h.get(k) in (None,"") and row.get(k) not in (None,""):h[k]=row.get(k)
        if row.get("recentRaces"):h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)
    for row in data.get("netkeibaRows") or []:
        h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
        if not h:continue
        sources.append("netkeiba") if "netkeiba" not in sources else None
        for k in ("sex","age","carriedWeight","jockey","trainer","bodyWeight","bodyWeightChange","owner","producer"):
            if (h.get(k) in (None,"",0)) and row.get(k) not in (None,""):h[k]=row.get(k)
        if row.get("pedigree"):h["pedigree"]={**(h.get("pedigree") or {}),**row.get("pedigree")}
        if row.get("_netkeibaHorseId"):h["_netkeibaHorseId"]=row.get("_netkeibaHorseId")
        if row.get("recentRaces"):
            h["recentRaces"]=_jra_merge_runs(h.get("recentRaces") or [],row.get("recentRaces") or [],5)
    for b in data.get("extra") or []:
        src=str(b.get("source") or "補助")
        for row in b.get("rows") or []:
            h=by_no.get(int(row.get("horseNumber") or 0)) or by_name.get(str(row.get("name") or "").strip())
            if h:
                extra=_strip_excluded(row.get("extra") or {})
                h.setdefault("extraSources",{})[src]=extra
                for key in ("pedigree","jockeyStats","trainerStats","jumpJockeyStats","jumpTrainerStats","jumpStats","isTransfer","transferFrom","ten1f","agari3f","pedigreeScore","distanceSuitabilityScore","surfaceSuitabilityScore","drawScore","bodyWeightScore","opponentLevelScore","lapScore","conditionChangeScore","jockeyScore","trainerScore","jumpJockeyScore","jumpTrainerScore"):
                    if extra.get(key) is not None:h[key]=extra[key]
                if isinstance(extra.get("allPastRuns"),list):h["allPastRuns"]=extra["allPastRuns"]
        if src not in sources:sources.append(src)
    base=list(detail.get("dataSources") or []);official="JRA公式" if detail.get("circuit")=="中央" else "NAR公式"
    for s in [official]+sources:
        if s not in base:base.append(s)
    detail["dataSources"]=base;return detail


def _merge_current_card_fields(detail: dict, rows: list[dict], *, _now_jst) -> dict:
    if not rows:return detail
    by={int(x.get("horseNumber") or 0):x for x in rows if int(x.get("horseNumber") or 0)>0}
    changed=False
    for h in detail.get("horses",[]) or []:
        z=by.get(int(h.get("horseNumber") or 0))
        if not z:continue
        for k in ("bodyWeight","bodyWeightChange","carriedWeight","status","scratched"):
            if z.get(k) not in (None,"") and h.get(k)!=z.get(k):
                h[k]=z.get(k);changed=True
    if changed:
        detail["bodyWeightSource"]="NAR公式出馬表"
        detail["bodyWeightUpdatedAt"]=_now_jst().strftime("%H:%M:%S")
    return detail
