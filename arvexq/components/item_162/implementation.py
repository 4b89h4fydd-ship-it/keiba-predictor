"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/api/v1/central-status")
def central_status():
    store = CentralStore()
    try:
        coverage = store.coverage()
    finally:
        store.conn.close()
    return {
        "feedConfigured": bool(os.getenv("CENTRAL_FEED_URL")),
        "historyFeedConfigured": bool(os.getenv("CENTRAL_HISTORY_FEED_URL") or os.getenv("CENTRAL_FEED_URL")), "jraOfficialFallback": True,
        "historyUsesLiveFeedFallback": bool(not os.getenv("CENTRAL_HISTORY_FEED_URL") and os.getenv("CENTRAL_FEED_URL")),
        "ingestEnabled": bool(os.getenv("CENTRAL_INGEST_TOKEN")),
        "coverage": coverage,
        "recentRuns": 5,
    }

@app.get("/api/v1/central-schema")
def central_schema():
    return {
      "description":"中央本番フィードの正規化JSON。JRA-VAN等のライセンス済みデータをこの形式へ変換して送信します。",
      "requiredRaceFields":["date","track","raceNumber","distance","horses"],
      "horseFields":["horseNumber","frameNumber","name","age","sex","carriedWeight","jockey","trainer","jockeyStats","trainerStats","prizeMoneyAtRace","recentRaces"],
      "recommendedRecentRaceDepth":5,
      "recommendedPastFields":["date","track","distance","condition","weather","fieldSize","finish","timeSeconds","cornerPositions","carriedWeight","racePrize1"],
      "optionalResult":{"status":"確定","finishers":[{"finish":1,"horseNumber":1,"name":"馬名","timeSeconds":92.3,"cornerPositions":[2,2,1]}]},
    }

@app.get("/api/v1/collector-status")
def collector_status():
    with _commercial_collector_lock:
        return dict(_commercial_collector_state)

def _central_refresh_status(iso_date: str) -> dict:
    with _central_refresh_lock:
        return {"running": iso_date in _central_refresh_running, "last": _central_refresh_last.get(iso_date,0)}

def _enrichment_status(race_id:str)->dict:
    with _enrich_jobs_lock:
        st=_enrich_jobs.get(race_id);return dict(st) if st else {"status":"idle","sources":[],"error":""}

@app.get("/api/v1/data-core/status")
def data_core_status(date:str=Query(""),circuit:str=Query("")):
    ds=date or _today_iso();out=_data_core_day_status(ds,_clean(circuit))
    with _data_core_lock:out["collector"]=dict(_data_core_state)
    return out

@app.get("/api/v1/site-bootstrap-status")
def site_bootstrap_status(date: str = Query(...)):
    with _site_bootstrap_lock:state=dict(_site_bootstrap_state.get(date) or {})
    stored=DAY_BUNDLES.get(date,complete_only=True)
    state["persistedComplete"]=bool(stored)
    state["persistedUpdatedAt"]=int((stored or {}).get("updatedAtEpoch") or 0)
    return state

@app.get("/api/v1/local-refresh-status")
def local_refresh_status(date: str = Query(...)):
    key=f"live:{date}"
    with _live_refresh_lock:
        running=key in _live_refresh_running
        last=_live_refresh_last.get(key,0)
    try:
        count=len(nar_race_summaries(date))
    except Exception:
        count=0
    return {"running":running,"last":last,"count":count}

@app.get("/api/v1/central-refresh-status")
def central_refresh_status(date: str = Query(...)):
    st=_central_refresh_status(date)
    try: st["count"]=len(central_race_summaries(date,allow_network=False))
    except Exception: st["count"]=0
    return st

@app.get("/api/v1/prewarm-status")
def prewarm_status(date: str = Query(""), circuit: str = Query("")):
    key=f"{date}|{_clean(circuit) or 'all'}" if date else ""
    with _prewarm_lock:
        state=dict(_prewarm_state.get(key) or {}) if key else {k:dict(v) for k,v in _prewarm_state.items()}
    db=PREPARED_STORE.status(date,_clean(circuit))
    return {"build": "v107","state":state,"prepared":db}

@app.get("/api/v1/odds-auto-status")
def odds_auto_status():
    with _auto_odds_lock:return dict(_auto_odds_state)

@app.get("/api/v1/enrichment-status/{race_id}")
def enrichment_status(race_id:str):
    return _enrichment_status(race_id)

@app.get("/api/v1/enrichment-schema")
def enrichment_schema():
    return {"priority":"official-first","builtIn":["JRA公式","NAR公式","netkeiba"],"extraFeeds":{"env":"EXTRA_RACE_FEEDS","format":"NAME=url;NAME2=url2"},"note":"公開ページ/APIのみ。ログイン・CAPTCHA・規約で自動取得不可のサイトは対象外"}
