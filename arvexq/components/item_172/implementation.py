"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/health")
def health():
    try:
        nar_coverage = NarStore().coverage()
    except Exception:
        nar_coverage = {"minDate": None, "maxDate": None}
    try:
        central_coverage = CentralStore().coverage()
    except Exception:
        central_coverage = {"minDate": None, "maxDate": None, "count": 0}
    return {
        "status":"ok", "mode":"production-v325-home-race-boxes", "historyStarted":_history_started,
        "historyReady":_history_ready, "historyError":_history_error, "narCoverage":nar_coverage,
        "centralCoverage":central_coverage, "centralFeedConfigured":bool(os.getenv("CENTRAL_FEED_URL")), "jraOfficialFallback":True,
        "centralHistoryFeedConfigured":bool(os.getenv("CENTRAL_HISTORY_FEED_URL") or os.getenv("CENTRAL_FEED_URL")),
        "narHistoryMonths": max(2, min(8, int(os.getenv("NAR_HISTORY_WARM_MONTHS", "4")))),
    }

@app.get("/api/v1/runtime-status")
def runtime_status():
    with _fast_card_cv:
        queued=len(_fast_card_queue);running=len(_fast_card_running)
    with _commercial_collector_lock:collector=dict(_commercial_collector_state)
    return {
        "build":"v324","engine":PREDICTION_ENGINE_VERSION,"volatilityEngine":VOLATILITY_ENGINE_VERSION,"dataRoot":str(DATA_ROOT),
        "persistentLikely":str(DATA_ROOT).startswith("/var/data") or str(DATA_ROOT).startswith("/data/"),
        "fastCardQueue":queued,"fastCardRunning":running,"collector":collector,"siteBootstrap":True,"persistentDayBundle":True,"nonBlockingBootstrap":True,"autoOdds":True,
        "racedb":RACEDB.status(),
    }
