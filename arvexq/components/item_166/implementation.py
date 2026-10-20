"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/past-pack/{race_id}")
def past_pack(race_id:str):
    """Return locally available recent-race snapshots only; zero public web calls."""
    current=_prepared_get_fresh(race_id) or _racedb_get_fast(race_id) or _fast_local_race_detail(race_id)
    if not current:return {"raceId":race_id,"races":[]}
    ids=[];seen=set()
    for h in current.get("horses",[]) or []:
        for rr in (h.get("recentRaces") or [])[:5]:
            rid=str(rr.get("raceId") or "")
            if not rid and str(current.get("circuit") or "")=="地方" and rr.get("date") and rr.get("track") and int(rr.get("raceNumber") or 0):
                rid=f"nar-{rr['date']}-{rr['track']}-{int(rr['raceNumber']):02d}"
            if rid and rid not in seen:
                seen.add(rid);ids.append(rid)
            if len(ids)>=18:break
        if len(ids)>=18:break
    out=[]
    for rid in ids:
        d=_prepared_get_fresh(rid) or _racedb_get_fast(rid) or _fast_local_race_detail(rid)
        if d and (d.get("horses") or d.get("result")):out.append(_compact_display_snapshot(d))
    return {"raceId":race_id,"races":out,"count":len(out),"source":"local-only"}
