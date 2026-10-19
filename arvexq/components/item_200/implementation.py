"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.middleware("http")
async def _arvexq_timing(request: Request, call_next):
    started=time.perf_counter()
    response=await call_next(request)
    try:response.headers["X-ARVEXQ-ms"]=f"{(time.perf_counter()-started)*1000:.1f}"
    except Exception:pass
    return response

def _now_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo"))

def _today_iso():
    return _now_jst().strftime("%Y-%m-%d")

def _data_core_health_hash(field_key:str, item:dict)->str:
    raw=json.dumps([field_key,item.get("status"),item.get("completeness"),item.get("source"),item.get("note")],ensure_ascii=False,separators=(",",":"))
    return hashlib.sha1(raw.encode("utf-8","ignore")).hexdigest()

def _data_core_record_run(run_id:str,race_id:str,started:int,status:str,attempted:set[str],before:dict,after:dict,note:str=""):
    conn=sqlite3.connect(RACEDB.path,timeout=3)
    try:
        conn.execute("""INSERT OR REPLACE INTO collector_runs(run_id,race_id,started_at,finished_at,status,attempted_fields,before_json,after_json,note)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                     (run_id,race_id,started,int(time.time()),status,json.dumps(sorted(attempted),ensure_ascii=False),
                      json.dumps(before,ensure_ascii=False,separators=(",",":")),json.dumps(after,ensure_ascii=False,separators=(",",":")),str(note or "")[:600]))
        conn.commit()
    finally:conn.close()

@app.get("/build")
def build_info():
    return {
        "build":"v324","appVersion":"14.24-v325-home-race-boxes",
        "predictionEngine":"arvexq-prediction-removed",
        "navigation":"top-venue-race","recentRuns":5,
        "localFirst":True,"selectedRacePriority":0,"trackPrewarm":3,
        "commercialCollector":True,"duplicateUpdaterDisabled":True,
        "autoDiagnosis":True,"autoOdds":True,"oddsUsedInPrediction":False,"raceVolatility":"硬/標/荒/大荒・pre-race no-odds",
        "narHydration":"sync_daily/sync_month","history":"JRA one-page / NAR month cache",
        "raceDataBank":True,"browserDetailCache":True,"gzip":True,"liveEnvironment":True,"environmentRefreshSec":45,
    }

@app.get("/version.json")
def version_json():
    return Response('{"build":"v330","shell":"independent-production-boundaries","model":"arvexq-prediction-removed"}', media_type="application/json", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"})
