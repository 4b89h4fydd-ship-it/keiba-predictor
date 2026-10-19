"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/environment-pack")
def environment_pack(date: str = Query(...), circuit: str = Query(...), track: str = Query(...)):
    rows=nar_race_summaries(date) if circuit=="地方" else central_race_summaries(date,allow_network=False)
    rows=[r for r in rows if str(r.get("track") or "")==str(track)]
    out=[{
        "id":str(r.get("id") or ""),
        "raceNumber":int(r.get("raceNumber") or 0),
        "weather":str(r.get("weather") or "不明"),
        "condition":str(r.get("condition") or "不明"),
        "environmentMeta":r.get("environmentMeta") or {},
    } for r in rows if r.get("id")]
    # If today's environment is still missing, start background refresh but return immediately.
    if date==_today_iso() and any(x["weather"]=="不明" or x["condition"]=="不明" for x in out):
        _schedule_track_environment(date,circuit,track,False)
    return {"date":date,"circuit":circuit,"track":track,"races":out,"count":len(out),"source":"local-only"}
