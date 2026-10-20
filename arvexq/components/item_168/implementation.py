"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/payouts/{race_id}")
def payout_refresh(race_id:str):
    """Fetch only payouts; do not rebuild history/AI."""
    saved=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if not saved:raise HTTPException(status_code=404,detail="race not found")
    existing=((saved.get("result") or {}).get("payouts") or [])
    if existing:
        return {"raceId":race_id,"payouts":existing,"source":(saved.get("result") or {}).get("payoutSource") or "保存済み","cached":True}

    payouts=[];source="";error=""
    if race_id.startswith("nar-"):
        payouts,src=_fetch_nar_payouts_only(saved)
        source="NAR公式" if payouts else ""
        error="" if payouts else src
        if not payouts:
            try:
                nk=_netkeiba_current_result(saved) or {}
                payouts=nk.get("payouts") or []
                if payouts:source="netkeiba結果"
            except Exception as exc:
                error=(error+" | "+str(exc)).strip(" |")
    else:
        try:
            result_cname=str(saved.get("resultCname") or "")
            if not result_cname:
                cname=_jra_find_cname(str(saved.get("date") or ""),str(saved.get("track") or ""),int(saved.get("raceNumber") or 0))
                if cname:result_cname=_jra_result_cname_from_card(cname)
            official=_jra_parse_result(result_cname,saved) if result_cname else None
            payouts=((official or {}).get("result") or {}).get("payouts") or []
            if payouts:source="JRA公式"
        except Exception as exc:
            error=str(exc)
        if not payouts:
            try:
                nk=_netkeiba_current_result(saved) or {}
                payouts=nk.get("payouts") or []
                if payouts:source="netkeiba結果"
            except Exception as exc:
                error=(error+" | "+str(exc)).strip(" |")

    if payouts:
        for store_get,store_put in (
            (lambda:PREPARED_STORE.get(race_id)[0],lambda d:PREPARED_STORE.put(d,force=True)),
            (lambda:RACEDB.get_race(race_id)[0],lambda d:RACEDB.upsert_race(d)),
        ):
            try:
                d=store_get()
                if not d:continue
                res=d.get("result")
                if not isinstance(res,dict):res={};d["result"]=res
                res["payouts"]=payouts;res["payoutSource"]=source;res.pop("payoutError",None)
                store_put(d)
            except Exception as exc:
                print("payout snapshot patch failed",race_id,exc)
    return {"raceId":race_id,"payouts":payouts,"source":source,"cached":False,"error":error[:240]}
